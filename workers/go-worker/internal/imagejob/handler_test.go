package imagejob

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"sync"
	"testing"
	"time"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/failure"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/provider"
)

const imageID = "7d1e2f3a-4b5c-4d6e-8f9a-0b1c2d3e4f5a"

type memStorage struct {
	mu      sync.Mutex
	objects map[string][]byte
	failPut bool
}

func (m *memStorage) Exists(_ context.Context, key string) (bool, int64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	data, ok := m.objects[key]
	return ok, int64(len(data)), nil
}

func (m *memStorage) Put(_ context.Context, key string, data []byte, _ string) error {
	if m.failPut {
		return errors.New("disco cheio")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.objects[key] = data
	return nil
}

type memPublisher struct {
	events []events.Envelope
	fail   bool
}

func (p *memPublisher) Publish(_ context.Context, env events.Envelope) error {
	if p.fail {
		return errors.New("broker fora")
	}
	p.events = append(p.events, env)
	return nil
}

func (p *memPublisher) types() []string {
	out := []string{}
	for _, e := range p.events {
		out = append(out, e.EventType)
	}
	return out
}

type memGuard struct {
	done   map[string]bool
	locked map[string]bool
	budget int
	used   int
}

func (g *memGuard) IsDone(_ context.Context, id string) (bool, error) { return g.done[id], nil }
func (g *memGuard) MarkDone(_ context.Context, id string) error       { g.done[id] = true; return nil }
func (g *memGuard) Lock(_ context.Context, id string, _ time.Duration) (func(), bool, error) {
	if g.locked[id] {
		return func() {}, false, nil
	}
	g.locked[id] = true
	return func() { delete(g.locked, id) }, true, nil
}
func (g *memGuard) ReserveBudget(_ context.Context, limit int) (bool, error) {
	g.used++
	return g.used <= limit, nil
}

type countingProvider struct {
	provider.Provider
	calls int
	err   error
	data  []byte
}

func (c *countingProvider) Generate(ctx context.Context, prompt, size string) (provider.Image, error) {
	c.calls++
	if c.err != nil {
		return provider.Image{}, c.err
	}
	if c.data != nil {
		return provider.Image{Data: c.data, ContentType: "image/png"}, nil
	}
	return c.Provider.Generate(ctx, prompt, size)
}

type fixture struct {
	h        *Handler
	storage  *memStorage
	pub      *memPublisher
	guard    *memGuard
	provider *countingProvider
}

func newFixture() *fixture {
	f := &fixture{
		storage:  &memStorage{objects: map[string][]byte{}},
		pub:      &memPublisher{},
		guard:    &memGuard{done: map[string]bool{}, locked: map[string]bool{}},
		provider: &countingProvider{Provider: provider.Fake{}},
	}
	f.h = &Handler{
		Provider: f.provider, Storage: f.storage, Publisher: f.pub, Guard: f.guard,
		DailyBudget: 100, Logger: slog.New(slog.NewTextHandler(io.Discard, nil)),
	}
	return f
}

func request(t *testing.T, theme string) events.Envelope {
	t.Helper()
	id := imageID
	env, err := events.New(events.AIImageRequested, events.AIImageRequestedV1{
		ImageID:    id,
		Prompt:     "Ilustração infantil. Sem texto, sem violência e sem ambiente hospitalar. Tema: " + theme + ".",
		Size:       "1024x1024",
		StorageKey: events.ExpectedStorageKey(id),
	}, "corr-1", &id)
	if err != nil {
		t.Fatal(err)
	}
	return env
}

func failedPayload(t *testing.T, env events.Envelope) events.AIImageFailedV1 {
	t.Helper()
	var p events.AIImageFailedV1
	if err := json.Unmarshal(env.Payload, &p); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestGeraGravaEPublica(t *testing.T) {
	f := newFixture()

	if err := f.h.Handle(context.Background(), request(t, "Floresta - Vogais"), false); err != nil {
		t.Fatal(err)
	}

	if got := f.pub.types(); len(got) != 2 || got[0] != events.AIImageStarted || got[1] != events.AIImageGenerated {
		t.Fatalf("eventos: %v", got)
	}
	var gen events.AIImageGeneratedV1
	_ = json.Unmarshal(f.pub.events[1].Payload, &gen)
	stored := f.storage.objects[events.ExpectedStorageKey(imageID)]
	if len(stored) == 0 || gen.SizeBytes != int64(len(stored)) || gen.Provider != "fake" {
		t.Fatalf("resultado incoerente: %+v (%d bytes gravados)", gen, len(stored))
	}
	if f.pub.events[1].CorrelationID != "corr-1" || *f.pub.events[1].JobID != imageID {
		t.Fatal("correlation_id/job_id não propagados")
	}
	if !f.guard.done[imageID] || len(f.guard.locked) != 0 {
		t.Fatal("job deveria estar concluído e destravado")
	}
}

func TestMensagemDuplicadaNaoChamaOProvedor(t *testing.T) {
	f := newFixture()
	env := request(t, "Vogais")
	_ = f.h.Handle(context.Background(), env, false)

	if err := f.h.Handle(context.Background(), env, false); err != nil {
		t.Fatal(err)
	}
	if f.provider.calls != 1 || len(f.pub.events) != 2 {
		t.Fatalf("provedor chamado %d vezes, %d eventos", f.provider.calls, len(f.pub.events))
	}
}

func TestImagemJaNoStorageNaoChamaOProvedor(t *testing.T) {
	// caiu depois de gravar e antes de publicar: na reentrega não paga de novo
	f := newFixture()
	f.storage.objects[events.ExpectedStorageKey(imageID)] = []byte("png-já-gravado")

	if err := f.h.Handle(context.Background(), request(t, "Vogais"), false); err != nil {
		t.Fatal(err)
	}
	if f.provider.calls != 0 || f.pub.types()[1] != events.AIImageGenerated {
		t.Fatalf("calls=%d eventos=%v", f.provider.calls, f.pub.types())
	}
}

func TestOutraReplicaProcessandoViraRetry(t *testing.T) {
	f := newFixture()
	f.guard.locked[imageID] = true

	err := f.h.Handle(context.Background(), request(t, "Vogais"), false)

	if err == nil || !failure.IsRetryable(err) || f.provider.calls != 0 {
		t.Fatalf("esperado retry sem chamar o provedor, veio %v", err)
	}
}

func TestTemaBloqueadoPelaModeracao(t *testing.T) {
	f := newFixture()

	if err := f.h.Handle(context.Background(), request(t, "Arma e sangue"), false); err != nil {
		t.Fatal(err)
	}
	last := f.pub.events[len(f.pub.events)-1]
	if last.EventType != events.AIImageFailed || failedPayload(t, last).ErrorCode != "moderation_rejected" {
		t.Fatalf("esperado failed/moderation_rejected, veio %v", f.pub.types())
	}
	if f.provider.calls != 0 || f.guard.used != 0 {
		t.Fatal("não deveria gastar orçamento nem chamar o provedor")
	}
}

func TestOrcamentoEsgotado(t *testing.T) {
	f := newFixture()
	f.h.DailyBudget = 0

	if err := f.h.Handle(context.Background(), request(t, "Vogais"), false); err != nil {
		t.Fatal(err)
	}
	last := f.pub.events[len(f.pub.events)-1]
	if failedPayload(t, last).ErrorCode != "budget_exceeded" || f.provider.calls != 0 {
		t.Fatalf("esperado budget_exceeded, veio %v", f.pub.types())
	}
}

func TestErroTemporarioDoProvedor(t *testing.T) {
	f := newFixture()
	f.provider.err = failure.Transient("provider_unavailable", "HTTP 503", nil)

	err := f.h.Handle(context.Background(), request(t, "Vogais"), false)
	if !failure.IsRetryable(err) {
		t.Fatalf("esperado erro temporário, veio %v", err)
	}
	if last := f.pub.events[len(f.pub.events)-1]; last.EventType == events.AIImageFailed {
		t.Fatal("não deveria publicar failed antes da última tentativa")
	}

	// última tentativa: registra a falha para o jogo e devolve o erro (vai para a DLQ)
	f.guard.locked = map[string]bool{}
	err = f.h.Handle(context.Background(), request(t, "Vogais"), true)
	last := f.pub.events[len(f.pub.events)-1]
	if err == nil || last.EventType != events.AIImageFailed || !failedPayload(t, last).Retryable {
		t.Fatalf("esperado failed retryable na última tentativa, veio %v / %v", err, f.pub.types())
	}
}

func TestErroPermanenteDoProvedor(t *testing.T) {
	f := newFixture()
	f.provider.err = failure.Permanent("moderation_rejected", "bloqueado", nil)

	if err := f.h.Handle(context.Background(), request(t, "Vogais"), false); err != nil {
		t.Fatal(err)
	}
	if failedPayload(t, f.pub.events[len(f.pub.events)-1]).ErrorCode != "moderation_rejected" {
		t.Fatal("falha não registrada")
	}
}

func TestSaidaQueNaoEhPNGERecusada(t *testing.T) {
	f := newFixture()
	f.provider.data = []byte("<html>não sou imagem</html>")

	if err := f.h.Handle(context.Background(), request(t, "Vogais"), false); err != nil {
		t.Fatal(err)
	}
	if failedPayload(t, f.pub.events[len(f.pub.events)-1]).ErrorCode != "invalid_output" {
		t.Fatal("deveria recusar saída inválida")
	}
	if len(f.storage.objects) != 0 {
		t.Fatal("nada deveria ser gravado")
	}
}

func TestPayloadForaDoContratoVaiParaDLQ(t *testing.T) {
	f := newFixture()
	env := request(t, "Vogais")
	env.Payload = json.RawMessage(`{"image_id":"` + imageID + `","prompt":"x","size":"1024x1024","storage_key":"ai-images/../../x.png"}`)

	err := f.h.Handle(context.Background(), env, false)

	if err == nil || failure.IsRetryable(err) {
		t.Fatalf("esperado erro permanente, veio %v", err)
	}
	if f.pub.types()[0] != events.AIImageFailed || f.provider.calls != 0 {
		t.Fatalf("esperado failed sem chamar o provedor, veio %v", f.pub.types())
	}
}

func TestStorageForaViraRetry(t *testing.T) {
	f := newFixture()
	f.storage.failPut = true

	if err := f.h.Handle(context.Background(), request(t, "Vogais"), false); !failure.IsRetryable(err) {
		t.Fatalf("esperado retry, veio %v", err)
	}
}
