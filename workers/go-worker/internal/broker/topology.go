// Package broker: topologia do RabbitMQ espelhada de
// app/infrastructure/messaging/topology.py. Os argumentos das exchanges
// compartilhadas precisam ser idênticos nos dois lados (senão o RabbitMQ
// responde PRECONDITION_FAILED). Cada consumidor declara só as próprias filas.
package broker

import (
	"fmt"

	amqp "github.com/rabbitmq/amqp091-go"
)

const (
	EventsExchange   = "apoiamais.events"
	RetryExchange    = "apoiamais.retry"
	DLXExchange      = "apoiamais.dlx"
	UnroutedExchange = "apoiamais.unrouted"
	UnroutedQueue    = "apoiamais.unrouted"

	DeliveryLimit = 10

	RetryCountHeader = "x-retry-count"
	ErrorHeader      = "x-last-error"
)

var RetryDelaysMS = []int{10_000, 60_000, 300_000}

func RetryQueueName(queue string, delayMS int) string {
	return fmt.Sprintf("%s.retry.%d", queue, delayMS)
}
func DLQName(queue string) string { return queue + ".dlq" }

// RetryDelayFor: attempt começa em 1; depois da última faixa repete a maior.
func RetryDelayFor(attempt int) int {
	if attempt < 1 {
		attempt = 1
	}
	if attempt > len(RetryDelaysMS) {
		attempt = len(RetryDelaysMS)
	}
	return RetryDelaysMS[attempt-1]
}

func DeclareExchanges(ch *amqp.Channel) error {
	if err := ch.ExchangeDeclare(UnroutedExchange, amqp.ExchangeFanout, true, false, false, false, nil); err != nil {
		return err
	}
	if _, err := ch.QueueDeclare(UnroutedQueue, true, false, false, false, amqp.Table{"x-queue-type": "quorum"}); err != nil {
		return err
	}
	if err := ch.QueueBind(UnroutedQueue, "", UnroutedExchange, false, nil); err != nil {
		return err
	}
	if err := ch.ExchangeDeclare(EventsExchange, amqp.ExchangeTopic, true, false, false, false,
		amqp.Table{"alternate-exchange": UnroutedExchange}); err != nil {
		return err
	}
	if err := ch.ExchangeDeclare(RetryExchange, amqp.ExchangeDirect, true, false, false, false, nil); err != nil {
		return err
	}
	return ch.ExchangeDeclare(DLXExchange, amqp.ExchangeDirect, true, false, false, false, nil)
}

func DeclareConsumerQueue(ch *amqp.Channel, queue string, bindings []string) error {
	if err := DeclareExchanges(ch); err != nil {
		return err
	}
	if _, err := ch.QueueDeclare(queue, true, false, false, false, amqp.Table{
		"x-queue-type":              "quorum",
		"x-dead-letter-exchange":    DLXExchange,
		"x-dead-letter-routing-key": queue,
		"x-delivery-limit":          int32(DeliveryLimit),
	}); err != nil {
		return err
	}
	for _, key := range bindings {
		if err := ch.QueueBind(queue, key, EventsExchange, false, nil); err != nil {
			return err
		}
	}
	for _, delay := range RetryDelaysMS {
		name := RetryQueueName(queue, delay)
		if _, err := ch.QueueDeclare(name, true, false, false, false, amqp.Table{
			"x-message-ttl":             int32(delay),
			"x-dead-letter-exchange":    "",
			"x-dead-letter-routing-key": queue,
		}); err != nil {
			return err
		}
		if err := ch.QueueBind(name, name, RetryExchange, false, nil); err != nil {
			return err
		}
	}
	dlq := DLQName(queue)
	if _, err := ch.QueueDeclare(dlq, true, false, false, false, amqp.Table{"x-queue-type": "quorum"}); err != nil {
		return err
	}
	return ch.QueueBind(dlq, queue, DLXExchange, false, nil)
}

// RetryCount lê x-retry-count aceitando os tipos inteiros que cada cliente AMQP usa.
func RetryCount(headers amqp.Table) int {
	switch v := headers[RetryCountHeader].(type) {
	case int:
		return v
	case int8:
		return int(v)
	case int16:
		return int(v)
	case int32:
		return int(v)
	case int64:
		return int(v)
	case uint8:
		return int(v)
	case uint16:
		return int(v)
	case uint32:
		return int(v)
	case float32:
		return int(v)
	case float64:
		return int(v)
	}
	return 0
}
