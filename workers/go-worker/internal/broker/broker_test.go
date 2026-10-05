package broker

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"os"
	"strings"
	"testing"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/failure"
)

func TestDecide(t *testing.T) {
	transient := failure.Transient("x", "y", nil)
	permanent := failure.Permanent("x", "y", nil)
	cases := []struct {
		err   error
		retry int
		want  Action
	}{
		{nil, 0, Ack},
		{transient, 0, Retry},
		{transient, 2, Retry},
		{transient, 3, DeadLetter},
		{errors.New("sem classificação"), 0, Retry},
		{permanent, 0, DeadLetter},
	}
	for _, c := range cases {
		if got := Decide(c.err, c.retry, 3); got != c.want {
			t.Errorf("Decide(%v, %d) = %v, quer %v", c.err, c.retry, got, c.want)
		}
	}
}

func TestRetryDelayFor(t *testing.T) {
	want := map[int]int{0: 10_000, 1: 10_000, 2: 60_000, 3: 300_000, 9: 300_000}
	for attempt, delay := range want {
		if got := RetryDelayFor(attempt); got != delay {
			t.Errorf("tentativa %d: %d, quer %d", attempt, got, delay)
		}
	}
}

func TestRetryCountAceitaTiposDeOutrosClientes(t *testing.T) {
	for _, v := range []any{int32(2), int64(2), int16(2), int(2), uint8(2), float64(2)} {
		if got := RetryCount(amqp.Table{RetryCountHeader: v}); got != 2 {
			t.Errorf("%T: %d", v, got)
		}
	}
	if RetryCount(amqp.Table{}) != 0 || RetryCount(amqp.Table{RetryCountHeader: "x"}) != 0 {
		t.Error("ausente ou inválido deveria ser 0")
	}
}

// Integração com RabbitMQ real (CI). AMQP_TEST_URL=amqp://user:pass@localhost:5672/
func TestIntegracaoRabbitMQ(t *testing.T) {
	url := os.Getenv("AMQP_TEST_URL")
	if url == "" {
		t.Skip("AMQP_TEST_URL não definido")
	}
	queue := "test.go-worker." + events.NewUUID()[:8]
	// event_type só aceita letras: sufixo aleatório sem dígitos
	suffix := strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return 'g' + (r - '0')
		}
		return r
	}, queue[len(queue)-8:])
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))

	conn, err := amqp.Dial(url)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	ch, err := conn.Channel()
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		for _, q := range []string{queue, DLQName(queue), queue + ".results",
			RetryQueueName(queue, 10_000), RetryQueueName(queue, 60_000), RetryQueueName(queue, 300_000)} {
			_, _ = ch.QueueDelete(q, false, false, false)
		}
	}()

	// fila de teste recebendo os resultados que o worker publica
	if err := DeclareExchanges(ch); err != nil {
		t.Fatal(err)
	}
	results := queue + ".results"
	if _, err := ch.QueueDeclare(results, false, false, false, false, nil); err != nil {
		t.Fatal(err)
	}
	topic := "test.result." + suffix
	if err := ch.QueueBind(results, topic, EventsExchange, false, nil); err != nil {
		t.Fatal(err)
	}

	inputTopic := "test.input." + suffix
	var b *Broker
	b = &Broker{
		URL: url, Queue: queue, Bindings: []string{inputTopic}, Concurrency: 2, MaxRetries: 0, Logger: logger,
		Handler: func(ctx context.Context, env events.Envelope, final bool) error {
			if string(env.Payload) == `{"fail":true}` {
				return failure.Transient("x", "falha simulada", nil)
			}
			out, _ := events.New(topic, map[string]string{"ok": "sim"}, env.CorrelationID, nil)
			return b.Publish(ctx, out)
		},
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { _ = b.Run(ctx); close(done) }()
	defer func() { cancel(); <-done }()

	deadline := time.Now().Add(10 * time.Second)
	for !b.Connected() && time.Now().Before(deadline) {
		time.Sleep(50 * time.Millisecond)
	}
	if !b.Connected() {
		t.Fatal("não conectou")
	}

	publish := func(payload string) {
		env, _ := events.New(inputTopic, json.RawMessage(payload), "corr-int", nil)
		if err := b.Publish(context.Background(), env); err != nil {
			t.Fatal(err)
		}
	}
	get := func(q string) *amqp.Delivery {
		limit := time.Now().Add(10 * time.Second)
		for time.Now().Before(limit) {
			d, ok, err := ch.Get(q, true)
			if err != nil {
				t.Fatal(err)
			}
			if ok {
				return &d
			}
			time.Sleep(100 * time.Millisecond)
		}
		return nil
	}

	publish(`{"ok":true}`)
	if d := get(results); d == nil || d.CorrelationId != "corr-int" {
		t.Fatal("resultado não publicado")
	}

	publish(`{"fail":true}`)
	d := get(DLQName(queue))
	if d == nil {
		t.Fatal("mensagem com falha não chegou na DLQ")
	}
	if RetryCount(d.Headers) != 0 || d.Headers[ErrorHeader] == nil {
		t.Fatalf("cabeçalhos inesperados: %v", d.Headers)
	}
}
