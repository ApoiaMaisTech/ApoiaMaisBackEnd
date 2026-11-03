//! Fluxo completo contra o RabbitMQ real. Precisa de AMQP_TEST_URL (o CI sobe o
//! RabbitMQ como serviço); sem a variável, os testes passam sem fazer nada.
//!
//! Cada teste usa uma fila própria e um correlation_id próprio, e os testes rodam
//! um de cada vez (LOCK): todas as filas de teste recebem `evaluation.requested`, e
//! publicar numa fila quorum que outro teste está apagando derruba o canal.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use lapin::options::{
    BasicGetOptions, BasicPublishOptions, ConfirmSelectOptions, QueueBindOptions,
    QueueDeclareOptions, QueueDeleteOptions,
};
use lapin::types::FieldTable;
use lapin::{BasicProperties, Channel, Connection, ConnectionProperties};
use rust_evaluator::broker;
use rust_evaluator::config::Config;
use rust_evaluator::topology::{EVENTS_EXCHANGE, RETRY_DELAYS_MS, dlq_name, retry_queue_name};
use serde_json::{Value, json};
use tokio::sync::watch;

static LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

fn amqp_url() -> Option<String> {
    std::env::var("AMQP_TEST_URL")
        .ok()
        .filter(|u| !u.is_empty())
}

struct Harness {
    channel: Channel,
    _connection: Connection,
    queue: String,
    results: String,
    stop: watch::Sender<bool>,
    worker: tokio::task::JoinHandle<()>,
}

impl Harness {
    async fn start(url: &str) -> Harness {
        let id = uuid::Uuid::new_v4().simple().to_string();
        let queue = format!("test.rust-evaluator.{}", &id[..8]);
        let cfg = Config {
            amqp_url: url.to_string(),
            queue: queue.clone(),
            prefetch: 4,
            max_retries: 3,
            max_message_bytes: 256 * 1024,
            drain_timeout: Duration::from_secs(5),
            health_addr: "127.0.0.1:0".into(),
        };
        let connection = Connection::connect(url, ConnectionProperties::default())
            .await
            .unwrap();
        let channel = connection.create_channel().await.unwrap();
        channel
            .confirm_select(ConfirmSelectOptions::default())
            .await
            .unwrap();

        let ready = Arc::new(AtomicBool::new(false));
        let (stop, stop_rx) = watch::channel(false);
        let worker_ready = ready.clone();
        let worker = tokio::spawn(async move { broker::run(cfg, stop_rx, worker_ready).await });
        for _ in 0..100 {
            if ready.load(Ordering::SeqCst) {
                break;
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
        assert!(ready.load(Ordering::SeqCst), "consumidor não ficou pronto");

        // fila que captura os resultados publicados em apoiamais.events
        let results = format!("test.rust-evaluator.results.{}", &id[..8]);
        channel
            .queue_declare(
                results.as_str().into(),
                QueueDeclareOptions {
                    auto_delete: true,
                    ..Default::default()
                },
                FieldTable::default(),
            )
            .await
            .unwrap();
        for key in ["evaluation.completed", "evaluation.failed"] {
            channel
                .queue_bind(
                    results.as_str().into(),
                    EVENTS_EXCHANGE.into(),
                    key.into(),
                    QueueBindOptions::default(),
                    FieldTable::default(),
                )
                .await
                .unwrap();
        }
        Harness {
            channel,
            _connection: connection,
            queue,
            results,
            stop,
            worker,
        }
    }

    async fn publish(&self, body: &[u8], correlation_id: &str) {
        self.channel
            .basic_publish(
                EVENTS_EXCHANGE.into(),
                "evaluation.requested".into(),
                BasicPublishOptions::default(),
                body,
                BasicProperties::default()
                    .with_content_type("application/json".into())
                    .with_delivery_mode(2)
                    .with_type("evaluation.requested".into())
                    .with_correlation_id(correlation_id.into()),
            )
            .await
            .unwrap()
            .await
            .unwrap();
    }

    /// Próximo resultado deste teste (filtra pelo correlation_id).
    async fn result(&self, correlation_id: &str) -> Option<Value> {
        self.get_from(&self.results.clone(), Some(correlation_id))
            .await
    }

    async fn get_from(&self, queue: &str, correlation_id: Option<&str>) -> Option<Value> {
        for _ in 0..100 {
            if let Some(message) = self
                .channel
                .basic_get(queue.into(), BasicGetOptions { no_ack: true })
                .await
                .unwrap()
            {
                let body: Value =
                    serde_json::from_slice(&message.delivery.data).unwrap_or(Value::Null);
                match correlation_id {
                    Some(id) if body["correlation_id"] != json!(id) => continue,
                    _ => return Some(body),
                }
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
        None
    }

    async fn stop(self) {
        let _ = self.stop.send(true);
        let _ = tokio::time::timeout(Duration::from_secs(10), self.worker).await;
        let mut names = vec![
            self.queue.clone(),
            dlq_name(&self.queue),
            self.results.clone(),
        ];
        names.extend(
            RETRY_DELAYS_MS
                .iter()
                .map(|d| retry_queue_name(&self.queue, *d)),
        );
        for name in names {
            let _ = self
                .channel
                .queue_delete(name.as_str().into(), QueueDeleteOptions::default())
                .await;
        }
    }
}

fn request(correlation_id: &str, payload: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({
        "event_id": uuid::Uuid::new_v4().to_string(),
        "event_type": "evaluation.requested",
        "version": 1,
        "occurred_at": "2026-11-03T12:00:00Z",
        "producer": "apoiamais-api",
        "correlation_id": correlation_id,
        "job_id": null,
        "payload": payload,
    }))
    .unwrap()
}

fn unique(prefix: &str) -> String {
    format!(
        "{prefix}-{}",
        &uuid::Uuid::new_v4().simple().to_string()[..10]
    )
}

#[tokio::test]
async fn pedido_valido_gera_completed() {
    let Some(url) = amqp_url() else { return };
    let _guard = LOCK.lock().await;
    let h = Harness::start(&url).await;
    let cid = unique("ok");
    let evaluation_id = uuid::Uuid::new_v4().to_string();

    h.publish(
        &request(
            &cid,
            json!({"evaluation_id": evaluation_id, "items": [
                {"item_id": "a", "kind": "text", "answer": ["Casa"], "expected": ["casa"]},
                {"item_id": "b", "kind": "number", "answer": ["2"], "expected": ["3"]}
            ]}),
        ),
        &cid,
    )
    .await;

    let result = h.result(&cid).await.expect("sem resultado");
    assert_eq!(result["event_type"], "evaluation.completed");
    assert_eq!(result["producer"], "rust-evaluator");
    assert_eq!(result["payload"]["evaluation_id"], json!(evaluation_id));
    assert_eq!(result["payload"]["correct_items"], 1);
    assert_eq!(result["payload"]["score"], 0.5);
    h.stop().await;
}

#[tokio::test]
async fn pedido_fora_do_contrato_gera_failed() {
    let Some(url) = amqp_url() else { return };
    let _guard = LOCK.lock().await;
    let h = Harness::start(&url).await;
    let cid = unique("invalido");

    h.publish(
        &request(
            &cid,
            json!({"evaluation_id": uuid::Uuid::new_v4().to_string(), "items": [
                {"item_id": "a", "kind": "text", "answer": [], "expected": ["casa"]}
            ]}),
        ),
        &cid,
    )
    .await;

    let result = h.result(&cid).await.expect("sem resultado");
    assert_eq!(result["event_type"], "evaluation.failed");
    assert_eq!(result["payload"]["error_code"], "invalid_request");
    assert_eq!(result["payload"]["retryable"], false);
    h.stop().await;
}

#[tokio::test]
async fn mensagem_malformada_vai_para_a_dlq_sem_perder() {
    let Some(url) = amqp_url() else { return };
    let _guard = LOCK.lock().await;
    let h = Harness::start(&url).await;
    let cid = unique("malformada");

    h.publish(b"{isto nao e json", &cid).await;

    let dead = h
        .channel
        .basic_get(
            dlq_name(&h.queue).as_str().into(),
            BasicGetOptions { no_ack: true },
        )
        .await
        .unwrap();
    let dead = match dead {
        Some(m) => Some(m),
        None => {
            let mut found = None;
            for _ in 0..100 {
                tokio::time::sleep(Duration::from_millis(50)).await;
                if let Some(m) = h
                    .channel
                    .basic_get(
                        dlq_name(&h.queue).as_str().into(),
                        BasicGetOptions { no_ack: true },
                    )
                    .await
                    .unwrap()
                {
                    found = Some(m);
                    break;
                }
            }
            found
        }
    };
    let dead = dead.expect("mensagem não chegou na DLQ");
    assert_eq!(dead.delivery.data, b"{isto nao e json");
    let headers = dead.delivery.properties.headers().clone().unwrap();
    assert!(headers.inner().get("x-last-error").is_some());
    h.stop().await;
}

#[tokio::test]
async fn reentrega_do_mesmo_pedido_gera_o_mesmo_event_id() {
    let Some(url) = amqp_url() else { return };
    let _guard = LOCK.lock().await;
    let h = Harness::start(&url).await;
    let cid = unique("dup");
    let body = request(
        &cid,
        json!({"evaluation_id": uuid::Uuid::new_v4().to_string(), "items": [
            {"item_id": "a", "kind": "choice", "answer": ["x"], "expected": ["x"]}
        ]}),
    );

    h.publish(&body, &cid).await;
    h.publish(&body, &cid).await;

    let first = h.result(&cid).await.expect("primeiro resultado");
    let second = h.result(&cid).await.expect("segundo resultado");
    // a API descarta o segundo pelo inbox (processed_event)
    assert_eq!(first["event_id"], second["event_id"]);
    h.stop().await;
}
