package events

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// mesmos exemplos validados pelo lado Python (tests/unit/test_event_contracts.py)
const examplesDir = "../../../../contracts/events/examples"

func readExample(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(examplesDir, name))
	if err != nil {
		t.Fatalf("lendo exemplo: %v", err)
	}
	return data
}

func TestExemplosDoContratoSaoAceitos(t *testing.T) {
	files, err := filepath.Glob(filepath.Join(examplesDir, "*.json"))
	if err != nil || len(files) == 0 {
		t.Fatalf("exemplos não encontrados: %v", err)
	}
	payloads := map[string]any{
		AIImageRequested: &AIImageRequestedV1{},
		AIImageStarted:   &AIImageStartedV1{},
		AIImageGenerated: &AIImageGeneratedV1{},
		AIImageFailed:    &AIImageFailedV1{},
	}
	for _, f := range files {
		env, err := ParseEnvelope(readExample(t, filepath.Base(f)))
		if err != nil {
			t.Fatalf("%s: %v", f, err)
		}
		target, ok := payloads[env.EventType]
		if !ok {
			t.Fatalf("%s: tipo sem struct: %s", f, env.EventType)
		}
		if err := DecodeStrict(env.Payload, target); err != nil {
			t.Fatalf("%s: payload: %v", f, err)
		}
	}
}

func TestRequestedValido(t *testing.T) {
	env, err := ParseEnvelope(readExample(t, "ai.image.requested.v1.json"))
	if err != nil {
		t.Fatal(err)
	}
	var req AIImageRequestedV1
	if err := DecodeStrict(env.Payload, &req); err != nil {
		t.Fatal(err)
	}
	if err := req.Validate(env.JobID); err != nil {
		t.Fatalf("exemplo deveria ser válido: %v", err)
	}
}

func TestRequestedInvalido(t *testing.T) {
	base := AIImageRequestedV1{
		ImageID:    "7d1e2f3a-4b5c-4d6e-8f9a-0b1c2d3e4f5a",
		Prompt:     "Tema: vogais",
		Size:       "1024x1024",
		StorageKey: "ai-images/7d1e2f3a4b5c4d6e8f9a0b1c2d3e4f5a.png",
	}
	other := "0b4f8a52-6f1e-4b8e-9a54-3d2c1f0e9a11"
	cases := map[string]func(*AIImageRequestedV1) *string{
		"path traversal": func(r *AIImageRequestedV1) *string { r.StorageKey = "ai-images/../../etc/passwd"; return nil },
		"chave de outro": func(r *AIImageRequestedV1) *string {
			r.StorageKey = "ai-images/0b4f8a526f1e4b8e9a543d2c1f0e9a11.png"
			return nil
		},
		"job_id diferente": func(r *AIImageRequestedV1) *string { return &other },
		"prompt vazio":     func(r *AIImageRequestedV1) *string { r.Prompt = ""; return nil },
		"prompt enorme":    func(r *AIImageRequestedV1) *string { r.Prompt = strings.Repeat("a", 1001); return nil },
		"size estranho":    func(r *AIImageRequestedV1) *string { r.Size = "4096x4096"; return nil },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			req := base
			jobID := mutate(&req)
			if err := req.Validate(jobID); err == nil {
				t.Fatal("deveria ser inválido")
			}
		})
	}
}

func TestEnvelopeComCampoDesconhecidoERecusado(t *testing.T) {
	var raw map[string]any
	_ = json.Unmarshal(readExample(t, "ai.image.started.v1.json"), &raw)
	raw["extra"] = 1
	data, _ := json.Marshal(raw)

	if _, err := ParseEnvelope(data); err == nil {
		t.Fatal("campo extra deveria ser recusado")
	}
}

func TestNovoEventoRespeitaOContrato(t *testing.T) {
	jobID := "7d1e2f3a-4b5c-4d6e-8f9a-0b1c2d3e4f5a"
	env, err := New(AIImageGenerated, AIImageGeneratedV1{
		ImageID: jobID, StorageKey: ExpectedStorageKey(jobID), MimeType: "image/png",
		SizeBytes: 10, Provider: "fake", Model: "placeholder-v1",
	}, "corr-1", &jobID)
	if err != nil {
		t.Fatal(err)
	}
	data, _ := json.Marshal(env)
	back, err := ParseEnvelope(data)
	if err != nil {
		t.Fatalf("ida e volta: %v", err)
	}
	if back.Producer != Producer || back.CorrelationID != "corr-1" || *back.JobID != jobID {
		t.Fatalf("campos não preservados: %+v", back)
	}
}

func TestNewUUIDEhV4(t *testing.T) {
	seen := map[string]bool{}
	for i := 0; i < 1000; i++ {
		id := NewUUID()
		if !ValidUUID(id) || id[14] != '4' || !strings.ContainsRune("89ab", rune(id[19])) {
			t.Fatalf("uuid inválido: %s", id)
		}
		if seen[id] {
			t.Fatal("uuid repetido")
		}
		seen[id] = true
	}
}
