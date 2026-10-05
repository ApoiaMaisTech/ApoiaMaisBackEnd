package provider

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"image/png"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/failure"
)

func TestFakeGeraPNGDeterministico(t *testing.T) {
	a, err := Fake{}.Generate(context.Background(), "tema", "1024x1024")
	if err != nil {
		t.Fatal(err)
	}
	b, _ := Fake{}.Generate(context.Background(), "tema", "1024x1024")
	if _, err := png.Decode(bytes.NewReader(a.Data)); err != nil {
		t.Fatalf("não é PNG: %v", err)
	}
	if !bytes.Equal(a.Data, b.Data) {
		t.Fatal("deveria ser determinístico")
	}
}

func openAIServer(t *testing.T, status int, body string, seen *map[string]any) *OpenAI {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/images/generations" || r.Header.Get("Authorization") != "Bearer chave" {
			t.Errorf("requisição inesperada: %s %s", r.URL.Path, r.Header.Get("Authorization"))
		}
		raw, _ := io.ReadAll(r.Body)
		if seen != nil {
			_ = json.Unmarshal(raw, seen)
		}
		w.WriteHeader(status)
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(srv.Close)
	return NewOpenAI("chave", srv.URL, "gpt-image-1", 5*time.Second)
}

func TestOpenAISucessoSoEnviaOPrompt(t *testing.T) {
	img, _ := Fake{}.Generate(context.Background(), "x", "")
	body := `{"data":[{"b64_json":"` + base64.StdEncoding.EncodeToString(img.Data) + `"}]}`
	var seen map[string]any
	p := openAIServer(t, 200, body, &seen)

	got, err := p.Generate(context.Background(), "Tema: vogais", "1024x1024")
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got.Data, img.Data) {
		t.Fatal("imagem diferente")
	}
	if _, hasUser := seen["user"]; hasUser {
		t.Fatal("não pode enviar identificador de usuário")
	}
	if seen["prompt"] != "Tema: vogais" || seen["moderation"] != "auto" || seen["n"] != float64(1) {
		t.Fatalf("payload inesperado: %v", seen)
	}
}

func TestOpenAIClassificaErros(t *testing.T) {
	cases := []struct {
		status    int
		body      string
		retryable bool
		code      string
	}{
		{429, `{}`, true, "provider_unavailable"},
		{503, `{}`, true, "provider_unavailable"},
		{401, `{}`, true, "provider_unavailable"},
		{400, `{"error":{"code":"moderation_blocked","message":"x"}}`, false, "moderation_rejected"},
		{400, `{"error":{"code":"invalid_size"}}`, false, "provider_rejected"},
		{200, `{"data":[]}`, false, "invalid_output"},
	}
	for _, c := range cases {
		_, err := openAIServer(t, c.status, c.body, nil).Generate(context.Background(), "x", "1024x1024")
		if err == nil || failure.IsRetryable(err) != c.retryable || failure.CodeOf(err, "") != c.code {
			t.Errorf("HTTP %d %s: veio %v", c.status, c.body, err)
		}
	}
}

func TestOpenAITimeoutEhTemporario(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(300 * time.Millisecond)
	}))
	t.Cleanup(srv.Close)
	p := NewOpenAI("chave", srv.URL, "gpt-image-1", 50*time.Millisecond)

	_, err := p.Generate(context.Background(), "x", "1024x1024")
	if !failure.IsRetryable(err) || !strings.HasPrefix(failure.CodeOf(err, ""), "provider_") {
		t.Fatalf("esperado erro temporário, veio %v", err)
	}
}
