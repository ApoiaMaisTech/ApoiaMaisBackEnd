//! Decide o que fazer com uma mensagem, sem I/O (testável sem RabbitMQ).
//!
//! | entrada                                           | saída                                   |
//! |---------------------------------------------------|-----------------------------------------|
//! | envelope inválido, grande demais ou evento desconhecido | `Outcome::DeadLetter` (DLQ, sem retry) |
//! | payload fora do contrato, mas com `evaluation_id` | publica `evaluation.failed` (`invalid_request`) |
//! | payload fora do contrato e sem `evaluation_id`    | `Outcome::DeadLetter` (não há a quem responder) |
//! | pedido válido                                     | publica `evaluation.completed`          |
//!
//! O único erro temporário possível é publicar o resultado (broker): quem chama
//! faz o retry. Como a avaliação é determinística e o id do resultado também,
//! repetir é seguro.

use serde_json::Value;

use crate::evaluate::evaluate;
use crate::events::{
    EVALUATION_COMPLETED, EVALUATION_FAILED, EVALUATION_REQUESTED, Envelope, EvaluationFailedV1,
    EvaluationRequestedV1, is_uuid, validate_request,
};

#[derive(Debug, PartialEq)]
pub enum Outcome {
    /// Publicar este evento em `apoiamais.events` (routing key = event_type) e dar ack.
    Publish(Envelope),
    /// Mensagem que nunca vai dar certo: vai para a DLQ com o motivo.
    DeadLetter(String),
}

pub fn handle(body: &[u8], max_message_bytes: usize) -> Outcome {
    if body.len() > max_message_bytes {
        return Outcome::DeadLetter(format!(
            "mensagem com {} bytes (limite {max_message_bytes})",
            body.len()
        ));
    }
    let request = match Envelope::parse(body) {
        Ok(envelope) => envelope,
        Err(err) => return Outcome::DeadLetter(format!("envelope inválido: {err}")),
    };
    if request.event_type != EVALUATION_REQUESTED || request.version != 1 {
        return Outcome::DeadLetter(format!(
            "evento não suportado: {} v{}",
            request.event_type, request.version
        ));
    }

    let payload: EvaluationRequestedV1 = match serde_json::from_value(request.payload.clone()) {
        Ok(payload) => payload,
        Err(err) => {
            return match evaluation_id_of(&request.payload) {
                Some(id) => failed(&request, id, format!("payload fora do contrato: {err}")),
                None => Outcome::DeadLetter("payload sem evaluation_id válido".into()),
            };
        }
    };
    if let Err(reason) = validate_request(&payload) {
        return match evaluation_id_of(&request.payload) {
            Some(id) => failed(&request, id, reason),
            None => Outcome::DeadLetter(reason),
        };
    }
    if request
        .job_id
        .as_deref()
        .is_some_and(|job_id| job_id != payload.evaluation_id)
    {
        return failed(
            &request,
            payload.evaluation_id.clone(),
            "job_id diferente de evaluation_id".into(),
        );
    }

    let completed = evaluate(&payload);
    Outcome::Publish(Envelope::result_for(
        &request,
        EVALUATION_COMPLETED,
        serde_json::to_value(completed).expect("resultado serializável"),
    ))
}

fn evaluation_id_of(payload: &Value) -> Option<String> {
    payload
        .get("evaluation_id")
        .and_then(Value::as_str)
        .filter(|id| is_uuid(id))
        .map(str::to_string)
}

fn failed(request: &Envelope, evaluation_id: String, reason: String) -> Outcome {
    let mut message: String = reason.chars().take(500).collect();
    if message.is_empty() {
        message = "pedido inválido".into();
    }
    let payload = EvaluationFailedV1 {
        evaluation_id,
        error_code: "invalid_request".into(),
        error_message: message,
        retryable: false,
    };
    Outcome::Publish(Envelope::result_for(
        request,
        EVALUATION_FAILED,
        serde_json::to_value(payload).expect("falha serializável"),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn request(payload: Value) -> Vec<u8> {
        serde_json::to_vec(&json!({
            "event_id": "6f1d2c3b-4a5e-4f60-8a7b-9c0d1e2f3a4b",
            "event_type": "evaluation.requested",
            "version": 1,
            "occurred_at": "2026-11-03T12:00:00Z",
            "producer": "apoiamais-api",
            "correlation_id": "req-1",
            "job_id": null,
            "payload": payload
        }))
        .unwrap()
    }

    const ID: &str = "0b8f3c2a-1d4e-4f5a-9b6c-7d8e9f0a1b2c";

    #[test]
    fn pedido_valido_vira_completed_com_id_deterministico() {
        let body = request(json!({"evaluation_id": ID, "items": [
            {"item_id": "a", "kind": "text", "answer": ["casa"], "expected": ["casa"]}
        ]}));

        let Outcome::Publish(first) = handle(&body, 1 << 20) else {
            panic!("esperava publicar")
        };
        let Outcome::Publish(second) = handle(&body, 1 << 20) else {
            panic!("esperava publicar")
        };

        assert_eq!(first.event_type, "evaluation.completed");
        assert_eq!(
            first.event_id, second.event_id,
            "reprocessar gera o mesmo event_id"
        );
        assert_eq!(first.correlation_id, "req-1");
        assert_eq!(first.payload["score"], json!(1.0));
    }

    #[test]
    fn payload_invalido_com_id_vira_failed() {
        let body = request(json!({"evaluation_id": ID, "items": [
            {"item_id": "a", "kind": "number", "answer": ["1"], "expected": ["um"]}
        ]}));

        let Outcome::Publish(event) = handle(&body, 1 << 20) else {
            panic!("esperava publicar")
        };

        assert_eq!(event.event_type, "evaluation.failed");
        assert_eq!(event.payload["error_code"], json!("invalid_request"));
        assert_eq!(event.payload["retryable"], json!(false));
        assert!(
            event.payload["error_message"]
                .as_str()
                .unwrap()
                .contains("gabarito numérico")
        );
    }

    #[test]
    fn campo_desconhecido_vira_failed() {
        let body = request(json!({"evaluation_id": ID, "patient_name": "Ana", "items": []}));
        let Outcome::Publish(event) = handle(&body, 1 << 20) else {
            panic!("esperava publicar")
        };
        assert_eq!(event.event_type, "evaluation.failed");
    }

    #[test]
    fn sem_evaluation_id_vai_para_a_dlq() {
        let body = request(json!({"items": []}));
        assert!(matches!(handle(&body, 1 << 20), Outcome::DeadLetter(_)));
    }

    #[test]
    fn envelope_quebrado_ou_evento_errado_vao_para_a_dlq() {
        assert!(matches!(
            handle(b"{nao json", 1 << 20),
            Outcome::DeadLetter(_)
        ));
        let mut wrong: Value =
            serde_json::from_slice(&request(json!({"evaluation_id": ID}))).unwrap();
        wrong["event_type"] = json!("ai.image.requested");
        assert!(matches!(
            handle(&serde_json::to_vec(&wrong).unwrap(), 1 << 20),
            Outcome::DeadLetter(_)
        ));
        wrong["event_type"] = json!("evaluation.requested");
        wrong["version"] = json!(2);
        assert!(matches!(
            handle(&serde_json::to_vec(&wrong).unwrap(), 1 << 20),
            Outcome::DeadLetter(_)
        ));
    }

    #[test]
    fn mensagem_grande_demais_vai_para_a_dlq() {
        let body = request(json!({"evaluation_id": ID, "items": []}));
        assert!(matches!(handle(&body, 10), Outcome::DeadLetter(_)));
    }

    #[test]
    fn item_repetido_e_texto_com_varias_respostas_sao_invalidos() {
        for items in [
            json!([{"item_id": "a", "kind": "choice", "answer": [], "expected": ["x"]},
                   {"item_id": "a", "kind": "choice", "answer": [], "expected": ["x"]}]),
            json!([{"item_id": "a", "kind": "text", "answer": ["x", "y"], "expected": ["x"]}]),
            json!([{"item_id": "a", "kind": "text", "answer": ["x"], "expected": ["x"], "max_typos": 4}]),
        ] {
            let body = request(json!({"evaluation_id": ID, "items": items}));
            let Outcome::Publish(event) = handle(&body, 1 << 20) else {
                panic!("esperava publicar")
            };
            assert_eq!(event.event_type, "evaluation.failed", "{items}");
        }
    }
}
