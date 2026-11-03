//! Contrato: os mesmos exemplos de `contracts/events/examples` que o Python e o Go leem.

use std::path::PathBuf;

use rust_evaluator::events::{
    Envelope, EvaluationCompletedV1, EvaluationFailedV1, EvaluationRequestedV1,
};
use rust_evaluator::handler::{Outcome, handle};
use serde_json::Value;

fn examples_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../contracts/events/examples")
}

fn example(name: &str) -> Vec<u8> {
    std::fs::read(examples_dir().join(name)).unwrap_or_else(|e| panic!("{name}: {e}"))
}

#[test]
fn todo_exemplo_tem_envelope_valido() {
    let mut count = 0;
    for entry in std::fs::read_dir(examples_dir()).unwrap() {
        let path = entry.unwrap().path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        Envelope::parse(&std::fs::read(&path).unwrap()).unwrap_or_else(|e| panic!("{path:?}: {e}"));
        count += 1;
    }
    assert!(count >= 7, "exemplos não encontrados");
}

#[test]
fn payloads_de_avaliacao_seguem_o_contrato() {
    let parse = |name: &str| Envelope::parse(&example(name)).unwrap().payload;
    serde_json::from_value::<EvaluationRequestedV1>(parse("evaluation.requested.v1.json")).unwrap();
    serde_json::from_value::<EvaluationCompletedV1>(parse("evaluation.completed.v1.json")).unwrap();
    serde_json::from_value::<EvaluationFailedV1>(parse("evaluation.failed.v1.json")).unwrap();
}

#[test]
fn exemplo_de_pedido_produz_exatamente_o_exemplo_de_resultado() {
    // o exemplo de evaluation.completed é a saída esperada do exemplo de evaluation.requested;
    // o Python valida esse mesmo exemplo contra o JSON Schema
    let request = Envelope::parse(&example("evaluation.requested.v1.json")).unwrap();
    let expected = Envelope::parse(&example("evaluation.completed.v1.json")).unwrap();

    let Outcome::Publish(result) = handle(&example("evaluation.requested.v1.json"), 1 << 20) else {
        panic!("esperava publicar o resultado");
    };

    assert_eq!(result.payload, expected.payload);
    assert_eq!(result.event_type, "evaluation.completed");
    assert_eq!(result.version, 1);
    assert_eq!(result.producer, "rust-evaluator");
    assert_eq!(result.correlation_id, request.correlation_id);
    assert_eq!(result.job_id, request.job_id);
    // o que sai é um envelope válido (mesmas regras de quem vai consumir)
    let reparsed = Envelope::parse(&result.to_json()).unwrap();
    assert_eq!(reparsed.payload, result.payload);
    let occurred_at =
        serde_json::from_slice::<Value>(&result.to_json()).unwrap()["occurred_at"].clone();
    assert!(occurred_at.as_str().unwrap().ends_with('Z'));
}

#[test]
fn campos_desconhecidos_sao_recusados() {
    let mut raw: Value = serde_json::from_slice(&example("evaluation.completed.v1.json")).unwrap();
    raw["extra"] = Value::Bool(true);
    assert!(Envelope::parse(&serde_json::to_vec(&raw).unwrap()).is_err());

    let mut payload = Envelope::parse(&example("evaluation.requested.v1.json"))
        .unwrap()
        .payload;
    payload["items"][0]["peso"] = Value::from(2);
    assert!(serde_json::from_value::<EvaluationRequestedV1>(payload).is_err());
}
