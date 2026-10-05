package broker

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"sync/atomic"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/failure"
)

// Handler processa um envelope. final=true na última tentativa permitida.
type Handler func(ctx context.Context, env events.Envelope, final bool) error

type Action int

const (
	Ack Action = iota
	Retry
	DeadLetter
)

// Decide o destino da mensagem a partir do erro do handler.
func Decide(err error, retryCount, maxRetries int) Action {
	switch {
	case err == nil:
		return Ack
	case !failure.IsRetryable(err):
		return DeadLetter
	case retryCount >= maxRetries:
		return DeadLetter
	default:
		return Retry
	}
}

// Broker mantém a conexão (com reconexão), consome uma fila e publica eventos
// com publisher confirms. Ack manual; prefetch = concorrência.
type Broker struct {
	URL         string
	Queue       string
	Bindings    []string
	Concurrency int
	MaxRetries  int
	Handler     Handler
	Logger      *slog.Logger

	connected atomic.Bool
	pubMu     sync.Mutex
	pubCh     *amqp.Channel
}

func (b *Broker) Connected() bool { return b.connected.Load() }

// Run consome até o contexto ser cancelado, reconectando com backoff.
func (b *Broker) Run(ctx context.Context) error {
	backoff := time.Second
	for {
		err := b.runOnce(ctx)
		b.connected.Store(false)
		if ctx.Err() != nil {
			return nil
		}
		b.Logger.Error("conexão com o RabbitMQ perdida; reconectando", "error", err, "backoff", backoff.String())
		select {
		case <-ctx.Done():
			return nil
		case <-time.After(backoff):
		}
		if backoff < 30*time.Second {
			backoff *= 2
		}
	}
}

func (b *Broker) runOnce(ctx context.Context) error {
	conn, err := amqp.DialConfig(b.URL, amqp.Config{Properties: amqp.Table{"connection_name": "go-worker"}})
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	defer conn.Close()

	consumeCh, err := conn.Channel()
	if err != nil {
		return err
	}
	pubCh, err := conn.Channel()
	if err != nil {
		return err
	}
	if err := pubCh.Confirm(false); err != nil {
		return fmt.Errorf("confirm: %w", err)
	}
	if err := DeclareConsumerQueue(consumeCh, b.Queue, b.Bindings); err != nil {
		return fmt.Errorf("topologia: %w", err)
	}
	if err := consumeCh.Qos(b.Concurrency, 0, false); err != nil {
		return err
	}
	deliveries, err := consumeCh.Consume(b.Queue, "go-worker", false, false, false, false, nil)
	if err != nil {
		return err
	}

	b.pubMu.Lock()
	b.pubCh = pubCh
	b.pubMu.Unlock()
	defer func() {
		b.pubMu.Lock()
		b.pubCh = nil
		b.pubMu.Unlock()
	}()

	closed := conn.NotifyClose(make(chan *amqp.Error, 1))
	b.connected.Store(true)
	b.Logger.Info("consumindo", "queue", b.Queue, "concurrency", b.Concurrency)

	var wg sync.WaitGroup
	defer wg.Wait() // termina o que está em andamento antes de fechar a conexão

	for {
		select {
		case <-ctx.Done():
			return nil
		case amqpErr := <-closed:
			return fmt.Errorf("conexão fechada: %v", amqpErr)
		case d, ok := <-deliveries:
			if !ok {
				return errors.New("canal de entregas fechado")
			}
			wg.Add(1)
			go func() {
				defer wg.Done()
				b.process(ctx, d)
			}()
		}
	}
}

func (b *Broker) process(ctx context.Context, d amqp.Delivery) {
	retryCount := RetryCount(d.Headers)
	log := b.Logger.With("message_id", d.MessageId, "correlation_id", d.CorrelationId, "retry", retryCount)

	env, err := events.ParseEnvelope(d.Body)
	if err != nil {
		err = failure.Permanent("invalid_envelope", "envelope inválido", err)
	} else {
		// o processamento termina mesmo se o worker receber SIGTERM no meio
		jobCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Minute)
		err = b.Handler(jobCtx, env, retryCount >= b.MaxRetries)
		cancel()
	}

	switch Decide(err, retryCount, b.MaxRetries) {
	case Ack:
		b.settle(d, log, d.Ack(false))
	case Retry:
		target := RetryQueueName(b.Queue, RetryDelayFor(retryCount+1))
		log.Warn("erro temporário, agendando retry", "error", err, "target", target)
		b.republish(d, log, RetryExchange, target, retryCount+1, err)
	case DeadLetter:
		log.Error("mensagem enviada para a DLQ", "error", err)
		b.republish(d, log, DLXExchange, b.Queue, retryCount, err)
	}
}

func (b *Broker) republish(d amqp.Delivery, log *slog.Logger, exchange, key string, retryCount int, cause error) {
	headers := amqp.Table{}
	for k, v := range d.Headers {
		headers[k] = v
	}
	headers[RetryCountHeader] = int32(retryCount)
	msg := fmt.Sprintf("%v", cause)
	if len(msg) > 300 {
		msg = msg[:300]
	}
	headers[ErrorHeader] = msg

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	err := b.publishRaw(ctx, exchange, key, amqp.Publishing{
		ContentType:   d.ContentType,
		DeliveryMode:  amqp.Persistent,
		MessageId:     d.MessageId,
		CorrelationId: d.CorrelationId,
		Type:          d.Type,
		Timestamp:     time.Now().UTC(),
		Headers:       headers,
		Body:          d.Body,
	})
	if err != nil {
		// não conseguiu mover: devolve para a fila (x-delivery-limit evita loop infinito)
		log.Error("falha ao republicar; devolvendo para a fila", "error", err)
		b.settle(d, log, d.Nack(false, true))
		return
	}
	b.settle(d, log, d.Ack(false))
}

func (b *Broker) settle(_ amqp.Delivery, log *slog.Logger, err error) {
	if err != nil {
		// canal caiu: a mensagem volta sozinha e a idempotência resolve a repetição
		log.Warn("falha ao confirmar mensagem", "error", err)
	}
}

// Publish publica um evento no apoiamais.events e espera o confirm do broker.
func (b *Broker) Publish(ctx context.Context, env events.Envelope) error {
	body, err := json.Marshal(env)
	if err != nil {
		return err
	}
	return b.publishRaw(ctx, EventsExchange, env.EventType, amqp.Publishing{
		ContentType:   "application/json",
		DeliveryMode:  amqp.Persistent,
		MessageId:     env.EventID,
		CorrelationId: env.CorrelationID,
		Type:          env.EventType,
		Timestamp:     env.OccurredAt,
		Body:          body,
	})
}

func (b *Broker) publishRaw(ctx context.Context, exchange, key string, msg amqp.Publishing) error {
	b.pubMu.Lock()
	ch := b.pubCh
	if ch == nil {
		b.pubMu.Unlock()
		return errors.New("sem conexão com o broker")
	}
	confirm, err := ch.PublishWithDeferredConfirmWithContext(ctx, exchange, key, false, false, msg)
	b.pubMu.Unlock()
	if err != nil {
		return err
	}
	ok, err := confirm.WaitContext(ctx)
	if err != nil {
		return err
	}
	if !ok {
		return errors.New("broker recusou a mensagem (nack)")
	}
	return nil
}
