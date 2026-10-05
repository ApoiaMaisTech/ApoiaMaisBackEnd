// Package provider abstrai o provedor de geração de imagens.
// Só recebe o prompt (montado pela API a partir do tema da fase): nenhum dado
// de criança, usuário ou paciente sai daqui para o provedor externo.
package provider

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"io"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/failure"
)

type Image struct {
	Data        []byte
	ContentType string
}

type Provider interface {
	Name() string
	Model() string
	Generate(ctx context.Context, prompt, size string) (Image, error)
}

// Fake gera uma imagem local (gradiente determinístico pelo prompt), sem custo.
// Padrão em desenvolvimento e nos testes.
type Fake struct{}

func (Fake) Name() string  { return "fake" }
func (Fake) Model() string { return "placeholder-v1" }

func (Fake) Generate(ctx context.Context, prompt, _ string) (Image, error) {
	if err := ctx.Err(); err != nil {
		return Image{}, failure.Transient("provider_unavailable", "cancelado", err)
	}
	seed := sha256.Sum256([]byte(prompt))
	const side = 256
	img := image.NewRGBA(image.Rect(0, 0, side, side))
	for y := 0; y < side; y++ {
		for x := 0; x < side; x++ {
			img.Set(x, y, color.RGBA{
				R: seed[0] ^ uint8(x),
				G: seed[1] ^ uint8(y),
				B: seed[2] ^ uint8((x+y)/2),
				A: 255,
			})
		}
	}
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return Image{}, err
	}
	return Image{Data: buf.Bytes(), ContentType: "image/png"}, nil
}

// OpenAI chama POST /v1/images/generations. Não envia o campo "user" nem
// qualquer identificador: o prompt é o único dado enviado.
type OpenAI struct {
	apiKey  string
	baseURL string
	model   string
	client  *http.Client
}

const maxResponseBytes = 40 << 20

func NewOpenAI(apiKey, baseURL, model string, timeout time.Duration) *OpenAI {
	return &OpenAI{
		apiKey:  apiKey,
		baseURL: strings.TrimRight(baseURL, "/"),
		model:   model,
		client:  &http.Client{Timeout: timeout},
	}
}

func (o *OpenAI) Name() string  { return "openai" }
func (o *OpenAI) Model() string { return o.model }

type openAIRequest struct {
	Model          string `json:"model"`
	Prompt         string `json:"prompt"`
	Size           string `json:"size"`
	N              int    `json:"n"`
	Moderation     string `json:"moderation,omitempty"`
	ResponseFormat string `json:"response_format,omitempty"`
}

type openAIResponse struct {
	Data []struct {
		B64JSON string `json:"b64_json"`
	} `json:"data"`
	Error *struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

func (o *OpenAI) Generate(ctx context.Context, prompt, size string) (Image, error) {
	req := openAIRequest{Model: o.model, Prompt: prompt, Size: size, N: 1}
	if strings.HasPrefix(o.model, "gpt-image") {
		req.Moderation = "auto" // moderação do próprio provedor na entrada e na saída
	} else {
		req.ResponseFormat = "b64_json"
	}
	body, err := json.Marshal(req)
	if err != nil {
		return Image{}, err
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, o.baseURL+"/v1/images/generations", bytes.NewReader(body))
	if err != nil {
		return Image{}, err
	}
	httpReq.Header.Set("Authorization", "Bearer "+o.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := o.client.Do(httpReq)
	if err != nil {
		var netErr net.Error
		if errors.As(err, &netErr) || errors.Is(err, context.DeadlineExceeded) {
			return Image{}, failure.Transient("provider_timeout", "provedor não respondeu", err)
		}
		return Image{}, failure.Transient("provider_unavailable", "falha de rede", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return Image{}, failure.Transient("provider_unavailable", "resposta incompleta", err)
	}

	var parsed openAIResponse
	_ = json.Unmarshal(raw, &parsed)

	switch {
	case resp.StatusCode == http.StatusOK:
	case resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500:
		return Image{}, failure.Transient("provider_unavailable", fmt.Sprintf("HTTP %d", resp.StatusCode), nil)
	case resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden:
		// erro de configuração (chave): tenta de novo para dar tempo de corrigir e alertar
		return Image{}, failure.Transient("provider_unavailable", fmt.Sprintf("HTTP %d (credencial)", resp.StatusCode), nil)
	default:
		if parsed.Error != nil && strings.Contains(parsed.Error.Code, "moderation") {
			return Image{}, failure.Permanent("moderation_rejected", "bloqueado pela moderação do provedor", nil)
		}
		return Image{}, failure.Permanent("provider_rejected", fmt.Sprintf("HTTP %d", resp.StatusCode), nil)
	}

	if len(parsed.Data) == 0 || parsed.Data[0].B64JSON == "" {
		return Image{}, failure.Permanent("invalid_output", "resposta sem imagem", nil)
	}
	data, err := base64.StdEncoding.DecodeString(parsed.Data[0].B64JSON)
	if err != nil {
		return Image{}, failure.Permanent("invalid_output", "base64 inválido", err)
	}
	return Image{Data: data, ContentType: "image/png"}, nil
}
