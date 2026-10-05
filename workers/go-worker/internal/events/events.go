// Package events implementa o envelope padrão e os payloads de ai.image.* v1.
// Contratos: contracts/events/*.schema.json (os testes leem os exemplos de lá).
package events

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"regexp"
	"time"
)

const (
	Producer = "go-worker"

	AIImageRequested = "ai.image.requested"
	AIImageStarted   = "ai.image.started"
	AIImageGenerated = "ai.image.generated"
	AIImageFailed    = "ai.image.failed"
)

var (
	uuidRe          = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
	eventTypeRe     = regexp.MustCompile(`^[a-z]+(\.[a-z]+)+$`)
	correlationIDRe = regexp.MustCompile(`^[A-Za-z0-9._-]{1,64}$`)
	StorageKeyRe    = regexp.MustCompile(`^ai-images/[0-9a-f]{32}\.png$`)
	errorCodeRe     = regexp.MustCompile(`^[a-z_]{1,50}$`)
)

type Envelope struct {
	EventID       string          `json:"event_id"`
	EventType     string          `json:"event_type"`
	Version       int             `json:"version"`
	OccurredAt    time.Time       `json:"occurred_at"`
	Producer      string          `json:"producer"`
	CorrelationID string          `json:"correlation_id"`
	JobID         *string         `json:"job_id"`
	Payload       json.RawMessage `json:"payload"`
}

func (e Envelope) Validate() error {
	switch {
	case !uuidRe.MatchString(e.EventID):
		return fmt.Errorf("event_id inválido")
	case len(e.EventType) > 100 || !eventTypeRe.MatchString(e.EventType):
		return fmt.Errorf("event_type inválido")
	case e.Version < 1:
		return fmt.Errorf("version inválida")
	case e.OccurredAt.IsZero():
		return fmt.Errorf("occurred_at ausente")
	case e.Producer == "" || len(e.Producer) > 50:
		return fmt.Errorf("producer inválido")
	case !correlationIDRe.MatchString(e.CorrelationID):
		return fmt.Errorf("correlation_id inválido")
	case e.JobID != nil && !uuidRe.MatchString(*e.JobID):
		return fmt.Errorf("job_id inválido")
	case len(e.Payload) == 0 || e.Payload[0] != '{':
		return fmt.Errorf("payload deve ser objeto")
	}
	return nil
}

// DecodeStrict recusa campos desconhecidos (o contrato usa additionalProperties: false).
func DecodeStrict(data []byte, v any) error {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		return err
	}
	if dec.More() {
		return fmt.Errorf("dados extras após o JSON")
	}
	return nil
}

func ParseEnvelope(body []byte) (Envelope, error) {
	var env Envelope
	if err := DecodeStrict(body, &env); err != nil {
		return env, fmt.Errorf("envelope inválido: %w", err)
	}
	return env, env.Validate()
}

type AIImageRequestedV1 struct {
	ImageID    string `json:"image_id"`
	Prompt     string `json:"prompt"`
	Size       string `json:"size"`
	StorageKey string `json:"storage_key"`
}

func (p AIImageRequestedV1) Validate(jobID *string) error {
	switch {
	case !uuidRe.MatchString(p.ImageID):
		return fmt.Errorf("image_id inválido")
	case jobID != nil && *jobID != p.ImageID:
		return fmt.Errorf("job_id diferente de image_id")
	case p.Prompt == "" || len([]rune(p.Prompt)) > 1000:
		return fmt.Errorf("prompt inválido")
	case p.Size != "1024x1024":
		return fmt.Errorf("size não suportado")
	case !StorageKeyRe.MatchString(p.StorageKey):
		return fmt.Errorf("storage_key fora do padrão")
	case p.StorageKey != ExpectedStorageKey(p.ImageID):
		return fmt.Errorf("storage_key não corresponde ao image_id")
	}
	return nil
}

func ExpectedStorageKey(imageID string) string {
	return "ai-images/" + compactUUID(imageID) + ".png"
}

func compactUUID(id string) string {
	out := make([]byte, 0, 32)
	for i := 0; i < len(id); i++ {
		if id[i] != '-' {
			out = append(out, id[i])
		}
	}
	return string(out)
}

type AIImageStartedV1 struct {
	ImageID string `json:"image_id"`
}

type AIImageGeneratedV1 struct {
	ImageID    string `json:"image_id"`
	StorageKey string `json:"storage_key"`
	MimeType   string `json:"mime_type"`
	SizeBytes  int64  `json:"size_bytes"`
	Provider   string `json:"provider"`
	Model      string `json:"model"`
}

type AIImageFailedV1 struct {
	ImageID      string `json:"image_id"`
	ErrorCode    string `json:"error_code"`
	ErrorMessage string `json:"error_message"`
	Retryable    bool   `json:"retryable"`
}

func ValidErrorCode(code string) bool { return errorCodeRe.MatchString(code) }

func ValidUUID(id string) bool { return uuidRe.MatchString(id) }

// New monta um envelope deste produtor, encadeando correlation_id e job_id do evento de origem.
func New(eventType string, payload any, correlationID string, jobID *string) (Envelope, error) {
	raw, err := json.Marshal(payload)
	if err != nil {
		return Envelope{}, err
	}
	env := Envelope{
		EventID:       NewUUID(),
		EventType:     eventType,
		Version:       1,
		OccurredAt:    time.Now().UTC(),
		Producer:      Producer,
		CorrelationID: correlationID,
		JobID:         jobID,
		Payload:       raw,
	}
	return env, env.Validate()
}

// NewUUID gera um UUID v4 (sem dependência externa).
func NewUUID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		panic(err) // crypto/rand não falha em sistemas suportados
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
