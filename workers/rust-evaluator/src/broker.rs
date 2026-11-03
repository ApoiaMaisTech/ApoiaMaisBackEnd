//! Consumidor RabbitMQ com ack manual, prefetch, retry com backoff, DLQ,
//! publisher confirms, reconexão e encerramento limpo (drain).
//!
//! Mesmo comportamento do `EventConsumer` (Python) e do broker do go-worker:
//! - resultado publicado (confirmado pelo broker): ack;
//! - falha ao publicar o resultado (temporária): republica em `<fila>.retry.<ms>`
//!   com `x-retry-count + 1` e dá ack; esgotadas as tentativas, vai para a DLQ;
//! - mensagem inválida: DLQ direto;
//! - falha ao republicar: nack com requeue (o `x-delivery-limit` da fila quorum
//!   impede loop infinito).

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use futures_util::StreamExt;
use lapin::message::Delivery;
use lapin::options::{
    BasicAckOptions, BasicCancelOptions, BasicConsumeOptions, BasicNackOptions,
    BasicPublishOptions, BasicQosOptions, ConfirmSelectOptions, ExchangeDeclareOptions,
    QueueBindOptions, QueueDeclareOptions,
};
use lapin::types::{AMQPValue, FieldTable, LongString, ShortString};
use lapin::{BasicProperties, Channel, Connection, ConnectionProperties, ExchangeKind};
use tokio::sync::watch;
use tokio::task::JoinSet;
use tracing::{Instrument, error, info, info_span, warn};

use crate::config::Config;
use crate::events::{EVALUATION_REQUESTED, Envelope};
use crate::handler::{self, Outcome};
use crate::topology::{
    DELIVERY_LIMIT, DLX_EXCHANGE, ERROR_HEADER, EVENTS_EXCHANGE, RETRY_COUNT_HEADER,
    RETRY_DELAYS_MS, RETRY_EXCHANGE, UNROUTED_EXCHANGE, UNROUTED_QUEUE, dlq_name, retry_delay_for,
    retry_queue_name,
};

type BoxError = Box<dyn std::error::Error + Send + Sync>;

fn durable_exchange() -> ExchangeDeclareOptions {
    ExchangeDeclareOptions {
        durable: true,
        ..ExchangeDeclareOptions::default()
    }
}

fn durable_queue() -> QueueDeclareOptions {
    QueueDeclareOptions {
        durable: true,
        ..QueueDeclareOptions::default()
    }
}

fn table(entries: &[(&str, AMQPValue)]) -> FieldTable {
    let mut t = FieldTable::default();
    for (key, value) in entries {
        t.insert(ShortString::from(*key), value.clone());
    }
    t
}

fn text(value: &str) -> AMQPValue {
    AMQPValue::LongString(LongString::from(value))
}

/// Exchanges compartilhadas (argumentos idênticos aos do Python e do Go).
pub async fn declare_exchanges(ch: &Channel) -> lapin::Result<()> {
    ch.exchange_declare(
        UNROUTED_EXCHANGE.into(),
        ExchangeKind::Fanout,
        durable_exchange(),
        FieldTable::default(),
    )
    .await?;
    ch.queue_declare(
        UNROUTED_QUEUE.into(),
        durable_queue(),
        table(&[("x-queue-type", text("quorum"))]),
    )
    .await?;
    ch.queue_bind(
        UNROUTED_QUEUE.into(),
        UNROUTED_EXCHANGE.into(),
        "".into(),
        QueueBindOptions::default(),
        FieldTable::default(),
    )
    .await?;
    ch.exchange_declare(
        EVENTS_EXCHANGE.into(),
        ExchangeKind::Topic,
        durable_exchange(),
        table(&[("alternate-exchange", text(UNROUTED_EXCHANGE))]),
    )
    .await?;
    ch.exchange_declare(
        RETRY_EXCHANGE.into(),
        ExchangeKind::Direct,
        durable_exchange(),
        FieldTable::default(),
    )
    .await?;
    ch.exchange_declare(
        DLX_EXCHANGE.into(),
        ExchangeKind::Direct,
        durable_exchange(),
        FieldTable::default(),
    )
    .await
}

/// Fila do consumidor + filas de retry (TTL) + DLQ.
pub async fn declare_consumer_queue(
    ch: &Channel,
    queue: &str,
    bindings: &[&str],
) -> lapin::Result<()> {
    declare_exchanges(ch).await?;
    ch.queue_declare(
        queue.into(),
        durable_queue(),
        table(&[
            ("x-queue-type", text("quorum")),
            ("x-dead-letter-exchange", text(DLX_EXCHANGE)),
            ("x-dead-letter-routing-key", text(queue)),
            ("x-delivery-limit", AMQPValue::LongInt(DELIVERY_LIMIT)),
        ]),
    )
    .await?;
    for key in bindings {
        ch.queue_bind(
            queue.into(),
            EVENTS_EXCHANGE.into(),
            (*key).into(),
            QueueBindOptions::default(),
            FieldTable::default(),
        )
        .await?;
    }
    for delay in RETRY_DELAYS_MS {
        let name = retry_queue_name(queue, delay);
        ch.queue_declare(
            name.as_str().into(),
            durable_queue(),
            table(&[
                ("x-message-ttl", AMQPValue::LongInt(delay)),
                ("x-dead-letter-exchange", text("")),
                ("x-dead-letter-routing-key", text(queue)),
            ]),
        )
        .await?;
        ch.queue_bind(
            name.as_str().into(),
            RETRY_EXCHANGE.into(),
            name.as_str().into(),
            QueueBindOptions::default(),
            FieldTable::default(),
        )
        .await?;
    }
    let dlq = dlq_name(queue);
    ch.queue_declare(
        dlq.as_str().into(),
        durable_queue(),
        table(&[("x-queue-type", text("quorum"))]),
    )
    .await?;
    ch.queue_bind(
        dlq.as_str().into(),
        DLX_EXCHANGE.into(),
        queue.into(),
        QueueBindOptions::default(),
        FieldTable::default(),
    )
    .await
}

/// `x-retry-count` aceitando os tipos inteiros que cada cliente AMQP usa.
pub fn retry_count_of(headers: Option<&FieldTable>) -> u32 {
    let Some(value) = headers.and_then(|h| h.inner().get(RETRY_COUNT_HEADER)) else {
        return 0;
    };
    let n: i64 = match value {
        AMQPValue::ShortShortInt(v) => i64::from(*v),
        AMQPValue::ShortShortUInt(v) => i64::from(*v),
        AMQPValue::ShortInt(v) => i64::from(*v),
        AMQPValue::ShortUInt(v) => i64::from(*v),
        AMQPValue::LongInt(v) => i64::from(*v),
        AMQPValue::LongUInt(v) => i64::from(*v),
        AMQPValue::LongLongInt(v) => *v,
        AMQPValue::Float(v) => *v as i64,
        AMQPValue::Double(v) => *v as i64,
        _ => 0,
    };
    n.clamp(0, i64::from(u32::MAX)) as u32
}

fn properties(
    message_id: &str,
    event_type: &str,
    correlation_id: &str,
    headers: FieldTable,
) -> BasicProperties {
    BasicProperties::default()
        .with_content_type("application/json".into())
        .with_delivery_mode(2)
        .with_message_id(message_id.into())
        .with_type(event_type.into())
        .with_correlation_id(correlation_id.into())
        .with_headers(headers)
}

async fn publish_confirmed(
    ch: &Channel,
    exchange: &str,
    routing_key: &str,
    body: &[u8],
    props: BasicProperties,
) -> Result<(), BoxError> {
    let confirmation = ch
        .basic_publish(
            exchange.into(),
            routing_key.into(),
            BasicPublishOptions::default(),
            body,
            props,
        )
        .await?
        .await?;
    if confirmation.is_nack() {
        return Err("broker recusou a publicação (nack)".into());
    }
    Ok(())
}

/// Publica o resultado em `apoiamais.events` e espera o confirm do broker.
pub async fn publish_event(ch: &Channel, event: &Envelope) -> Result<(), BoxError> {
    let props = properties(
        &event.event_id,
        &event.event_type,
        &event.correlation_id,
        FieldTable::default(),
    );
    publish_confirmed(
        ch,
        EVENTS_EXCHANGE,
        &event.event_type,
        &event.to_json(),
        props,
    )
    .await
}

fn short_error(reason: &str) -> String {
    reason.chars().take(300).collect()
}

async fn republish(
    ch: &Channel,
    delivery: &Delivery,
    exchange: &str,
    routing_key: &str,
    attempt: u32,
    reason: &str,
) {
    let mut headers = delivery.properties.headers().clone().unwrap_or_default();
    headers.insert(
        RETRY_COUNT_HEADER.into(),
        AMQPValue::LongInt(attempt.min(i32::MAX as u32) as i32),
    );
    headers.insert(ERROR_HEADER.into(), text(&short_error(reason)));
    let p = &delivery.properties;
    let props = properties(
        p.message_id().as_ref().map(|s| s.as_str()).unwrap_or(""),
        p.kind().as_ref().map(|s| s.as_str()).unwrap_or(""),
        p.correlation_id()
            .as_ref()
            .map(|s| s.as_str())
            .unwrap_or(""),
        headers,
    );
    match publish_confirmed(ch, exchange, routing_key, &delivery.data, props).await {
        Ok(()) => {
            if let Err(err) = delivery.ack(BasicAckOptions::default()).await {
                warn!(error = %err, "falha ao confirmar mensagem");
            }
        }
        Err(err) => {
            error!(error = %err, "falha ao republicar; devolvendo para a fila");
            let _ = delivery
                .nack(BasicNackOptions {
                    requeue: true,
                    ..BasicNackOptions::default()
                })
                .await;
        }
    }
}

/// Processa uma entrega (uma task por mensagem; o prefetch limita quantas ao mesmo tempo).
pub async fn process_delivery(delivery: Delivery, ch: Arc<Channel>, cfg: Arc<Config>) {
    let retry_count = retry_count_of(delivery.properties.headers().as_ref());
    match handler::handle(&delivery.data, cfg.max_message_bytes) {
        Outcome::Publish(event) => match publish_event(&ch, &event).await {
            Ok(()) => {
                info!(result_event_id = %event.event_id, event_type = %event.event_type, "resultado publicado");
                if let Err(err) = delivery.ack(BasicAckOptions::default()).await {
                    // sem ack a mensagem volta; o resultado sai de novo com o mesmo event_id
                    warn!(error = %err, "falha ao confirmar mensagem");
                }
            }
            Err(err) => {
                let reason = format!("falha ao publicar resultado: {err}");
                if retry_count >= cfg.max_retries {
                    error!(error = %reason, "tentativas esgotadas, mensagem enviada para a DLQ");
                    republish(
                        &ch,
                        &delivery,
                        DLX_EXCHANGE,
                        &cfg.queue,
                        retry_count,
                        &reason,
                    )
                    .await;
                } else {
                    let attempt = retry_count + 1;
                    let target = retry_queue_name(&cfg.queue, retry_delay_for(attempt));
                    warn!(attempt, error = %reason, "erro temporário, agendando nova tentativa");
                    republish(&ch, &delivery, RETRY_EXCHANGE, &target, attempt, &reason).await;
                }
            }
        },
        Outcome::DeadLetter(reason) => {
            error!(error = %short_error(&reason), "mensagem inválida enviada para a DLQ");
            republish(
                &ch,
                &delivery,
                DLX_EXCHANGE,
                &cfg.queue,
                retry_count,
                &reason,
            )
            .await;
        }
    }
}

/// Consome até `shutdown`, reconectando com backoff exponencial (1 s .. 30 s).
pub async fn run(cfg: Config, mut shutdown: watch::Receiver<bool>, ready: Arc<AtomicBool>) {
    let cfg = Arc::new(cfg);
    let mut backoff = Duration::from_secs(1);
    loop {
        if *shutdown.borrow() {
            break;
        }
        match consume(cfg.clone(), &mut shutdown, &ready).await {
            Ok(()) => break,
            Err(err) => warn!(error = %err, "consumidor sem conexão com o RabbitMQ"),
        }
        ready.store(false, Ordering::SeqCst);
        if *shutdown.borrow() {
            break;
        }
        info!(
            backoff_seconds = backoff.as_secs(),
            "reconectando consumidor"
        );
        tokio::select! {
            _ = tokio::time::sleep(backoff) => {}
            _ = shutdown.changed() => {}
        }
        backoff = (backoff * 2).min(Duration::from_secs(30));
    }
}

/// Uma sessão de consumo. `Ok(())` = encerramento pedido; `Err` = conexão perdida.
pub async fn consume(
    cfg: Arc<Config>,
    shutdown: &mut watch::Receiver<bool>,
    ready: &AtomicBool,
) -> Result<(), BoxError> {
    let connection = Connection::connect(&cfg.amqp_url, ConnectionProperties::default()).await?;
    let consume_channel = connection.create_channel().await?;
    let publish_channel = Arc::new(connection.create_channel().await?);
    publish_channel
        .confirm_select(ConfirmSelectOptions::default())
        .await?;

    declare_consumer_queue(&consume_channel, &cfg.queue, &[EVALUATION_REQUESTED]).await?;
    consume_channel
        .basic_qos(cfg.prefetch, BasicQosOptions::default())
        .await?;
    let tag = format!("rust-evaluator-{}", uuid::Uuid::new_v4().simple());
    let mut consumer = consume_channel
        .basic_consume(
            cfg.queue.as_str().into(),
            tag.as_str().into(),
            BasicConsumeOptions::default(),
            FieldTable::default(),
        )
        .await?;

    ready.store(true, Ordering::SeqCst);
    info!(queue = %cfg.queue, prefetch = cfg.prefetch, "consumindo");

    let mut tasks = JoinSet::new();
    let outcome: Result<(), BoxError> = loop {
        tokio::select! {
            _ = shutdown.changed() => break Ok(()),
            Some(_) = tasks.join_next(), if !tasks.is_empty() => {}
            next = consumer.next() => match next {
                Some(Ok(delivery)) => {
                    let p = &delivery.properties;
                    let span = info_span!(
                        "message",
                        correlation_id = %p.correlation_id().as_ref().map(|s| s.as_str()).unwrap_or("-"),
                        event_id = %p.message_id().as_ref().map(|s| s.as_str()).unwrap_or("-"),
                        queue = %cfg.queue,
                    );
                    tasks.spawn(process_delivery(delivery, publish_channel.clone(), cfg.clone()).instrument(span));
                }
                Some(Err(err)) => break Err(err.into()),
                None => break Err("consumo cancelado pelo broker".into()),
            },
        }
    };
    ready.store(false, Ordering::SeqCst);

    // drain: para de receber e termina o que está em andamento antes de fechar
    let _ = consume_channel
        .basic_cancel(tag.as_str().into(), BasicCancelOptions::default())
        .await;
    if !tasks.is_empty() {
        info!(inflight = tasks.len(), "aguardando mensagens em andamento");
        let drained = tokio::time::timeout(cfg.drain_timeout, async {
            while tasks.join_next().await.is_some() {}
        })
        .await;
        if drained.is_err() {
            warn!(
                inflight = tasks.len(),
                "tempo de drain esgotado; mensagens serão reentregues"
            );
            tasks.abort_all();
        }
    }
    let _ = connection.close(200, "encerrando".into()).await;
    outcome
}
