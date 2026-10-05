// Package imagejob processa ai.image.requested:
//
//	valida -> idempotência (Redis) -> ai.image.started -> moderação do tema ->
//	orçamento -> provedor -> valida PNG -> storage -> ai.image.generated
//
// Falhas definitivas viram ai.image.failed (o jogo mostra a ilustração padrão).
// O worker nunca acessa o MySQL: o estado do job é da API.
package imagejob

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"image"
	_ "image/png" // registra o decoder PNG para image.DecodeConfig
	"log/slog"
	"net/http"
	"time"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/failure"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/moderation"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/provider"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/storage"
)

const (
	maxImageBytes = 20 << 20
	maxImageSide  = 4096
	lockTTL       = 10 * time.Minute
)

type Publisher interface {
	Publish(ctx context.Context, env events.Envelope) error
}

type Guard interface {
	IsDone(ctx context.Context, jobID string) (bool, error)
	MarkDone(ctx context.Context, jobID string) error
	Lock(ctx context.Context, jobID string, ttl time.Duration) (func(), bool, error)
	ReserveBudget(ctx context.Context, limit int) (bool, error)
}

type Handler struct {
	Provider    provider.Provider
	Storage     storage.Storage
	Publisher   Publisher
	Guard       Guard
	DailyBudget int
	Logger      *slog.Logger
}

// Handle devolve:
//   - nil: ack (inclusive quando a falha foi registrada com ai.image.failed)
//   - erro permanente: a mensagem é inválida e vai para a DLQ
//   - erro temporário: o consumidor agenda retry; se final=true, a falha é
//     registrada com ai.image.failed antes de a mensagem ir para a DLQ
func (h *Handler) Handle(ctx context.Context, env events.Envelope, final bool) error {
	if env.EventType != events.AIImageRequested || env.Version != 1 {
		return failure.Permanent("unsupported_event", env.EventType, nil)
	}
	var req events.AIImageRequestedV1
	if err := events.DecodeStrict(env.Payload, &req); err != nil {
		return failure.Permanent("invalid_request", "payload ilegível", err)
	}
	log := h.Logger.With("job_id", req.ImageID, "correlation_id", env.CorrelationID, "event_id", env.EventID)
	if err := req.Validate(env.JobID); err != nil {
		if events.ValidUUID(req.ImageID) {
			// image_id aproveitável: registra a falha para o jogo não esperar para sempre
			if pubErr := h.fail(ctx, env, req.ImageID, "invalid_request", err.Error(), false); pubErr != nil {
				log.Warn("não foi possível publicar ai.image.failed", "error", pubErr)
			}
		}
		return failure.Permanent("invalid_request", "payload fora do contrato", err)
	}

	err := h.process(ctx, env, req, log)
	if err == nil {
		return nil
	}

	var fe *failure.Error
	isClassified := errors.As(err, &fe)
	if isClassified && !fe.Retryable {
		log.Warn("geração falhou de forma definitiva", "code", fe.Code, "error", err)
		return h.fail(ctx, env, req.ImageID, fe.Code, fe.Message, false)
	}
	if final {
		code := failure.CodeOf(err, "provider_unavailable")
		log.Error("tentativas esgotadas", "code", code, "error", err)
		if pubErr := h.fail(ctx, env, req.ImageID, code, "tentativas esgotadas", true); pubErr != nil {
			return pubErr // continua temporário: o consumidor manda para a DLQ do mesmo jeito
		}
	}
	return err
}

func (h *Handler) process(ctx context.Context, env events.Envelope, req events.AIImageRequestedV1, log *slog.Logger) error {
	done, err := h.Guard.IsDone(ctx, req.ImageID)
	if err != nil {
		return failure.Transient("guard_unavailable", "redis indisponível", err)
	}
	if done {
		log.Info("job já concluído, mensagem duplicada ignorada")
		return nil
	}

	release, locked, err := h.Guard.Lock(ctx, req.ImageID, lockTTL)
	if err != nil {
		return failure.Transient("guard_unavailable", "redis indisponível", err)
	}
	if !locked {
		return failure.Transient("in_progress", "outra réplica está processando este job", nil)
	}
	defer release()

	jobID := req.ImageID
	if err := h.publish(ctx, env, events.AIImageStarted, events.AIImageStartedV1{ImageID: req.ImageID}, &jobID); err != nil {
		return err
	}

	exists, size, err := h.Storage.Exists(ctx, req.StorageKey)
	if err != nil {
		return failure.Transient("storage_unavailable", "falha ao consultar o storage", err)
	}
	providerName, model := h.Provider.Name(), h.Provider.Model()

	if !exists {
		// imagem ainda não existe: só aqui gastamos com o provedor
		if term := moderation.CheckPrompt(req.Prompt); term != "" {
			return failure.Permanent("moderation_rejected", "tema bloqueado pela moderação local", nil)
		}
		ok, err := h.Guard.ReserveBudget(ctx, h.DailyBudget)
		if err != nil {
			return failure.Transient("guard_unavailable", "redis indisponível", err)
		}
		if !ok {
			return failure.Permanent("budget_exceeded", "orçamento diário de imagens esgotado", nil)
		}

		started := time.Now()
		img, err := h.Provider.Generate(ctx, req.Prompt, req.Size)
		if err != nil {
			return err
		}
		if err := validatePNG(img.Data); err != nil {
			return failure.Permanent("invalid_output", "imagem inválida do provedor", err)
		}
		if err := h.Storage.Put(ctx, req.StorageKey, img.Data, "image/png"); err != nil {
			return failure.Transient("storage_unavailable", "falha ao gravar a imagem", err)
		}
		size = int64(len(img.Data))
		log.Info("imagem gerada", "provider", providerName, "model", model,
			"bytes", size, "prompt_chars", len([]rune(req.Prompt)), "duration_ms", time.Since(started).Milliseconds())
	} else {
		log.Info("imagem já estava no storage, provedor não foi chamado")
	}

	generated := events.AIImageGeneratedV1{
		ImageID:    req.ImageID,
		StorageKey: req.StorageKey,
		MimeType:   "image/png",
		SizeBytes:  size,
		Provider:   providerName,
		Model:      model,
	}
	if err := h.publish(ctx, env, events.AIImageGenerated, generated, &jobID); err != nil {
		return err
	}
	if err := h.Guard.MarkDone(ctx, req.ImageID); err != nil {
		log.Warn("não foi possível marcar o job como concluído", "error", err)
	}
	return nil
}

func (h *Handler) fail(ctx context.Context, env events.Envelope, imageID, code, message string, retryable bool) error {
	if !events.ValidErrorCode(code) {
		code = "unknown_error"
	}
	if len(message) > 500 {
		message = message[:500]
	}
	jobID := imageID
	payload := events.AIImageFailedV1{ImageID: imageID, ErrorCode: code, ErrorMessage: message, Retryable: retryable}
	return h.publish(ctx, env, events.AIImageFailed, payload, &jobID)
}

func (h *Handler) publish(ctx context.Context, origin events.Envelope, eventType string, payload any, jobID *string) error {
	env, err := events.New(eventType, payload, origin.CorrelationID, jobID)
	if err != nil {
		return failure.Permanent("invalid_event", "evento de saída inválido", err)
	}
	if err := h.Publisher.Publish(ctx, env); err != nil {
		return failure.Transient("broker_unavailable", "falha ao publicar "+eventType, err)
	}
	return nil
}

func validatePNG(data []byte) error {
	if len(data) == 0 || len(data) > maxImageBytes {
		return fmt.Errorf("tamanho inválido: %d bytes", len(data))
	}
	if ct := http.DetectContentType(data); ct != "image/png" {
		return fmt.Errorf("conteúdo não é PNG: %s", ct)
	}
	cfg, format, err := image.DecodeConfig(bytes.NewReader(data))
	if err != nil {
		return err
	}
	if format != "png" || cfg.Width <= 0 || cfg.Height <= 0 || cfg.Width > maxImageSide || cfg.Height > maxImageSide {
		return fmt.Errorf("dimensões inválidas: %dx%d", cfg.Width, cfg.Height)
	}
	return nil
}
