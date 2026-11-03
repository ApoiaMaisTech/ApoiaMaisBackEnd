//! Envelope padrão e payloads de `evaluation.*` v1.
//!
//! Contratos: `contracts/events/*.schema.json`. Os testes (`tests/contracts.rs`)
//! leem os mesmos exemplos que os testes do Python e do Go. Os structs recusam
//! campos desconhecidos, como o `additionalProperties: false` dos schemas.

use chrono::{DateTime, SecondsFormat, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use uuid::Uuid;

pub const PRODUCER: &str = "rust-evaluator";
pub const ENGINE: &str = "rust-evaluator";
pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");

pub const EVALUATION_REQUESTED: &str = "evaluation.requested";
pub const EVALUATION_COMPLETED: &str = "evaluation.completed";
pub const EVALUATION_FAILED: &str = "evaluation.failed";

pub const MAX_ITEMS: usize = 200;
pub const MAX_VALUES: usize = 50;
pub const MAX_TEXT_CHARS: usize = 500;
pub const MAX_TYPOS: u8 = 3;

/// Namespace dos ids determinísticos dos eventos de resultado (UUID v5).
const RESULT_NAMESPACE: Uuid = Uuid::from_u128(0x6a1f_43c2_9b8e_4d70_a5f1_3c2e_7b9d_0e14);

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Envelope {
    pub event_id: String,
    pub event_type: String,
    pub version: u32,
    pub occurred_at: DateTime<Utc>,
    pub producer: String,
    pub correlation_id: String,
    #[serde(default)]
    pub job_id: Option<String>,
    pub payload: Value,
}

#[derive(Debug, thiserror::Error, PartialEq)]
pub enum EnvelopeError {
    #[error("JSON inválido: {0}")]
    Json(String),
    #[error("{0} inválido")]
    Field(&'static str),
}

pub fn is_uuid(value: &str) -> bool {
    // formato do contrato: minúsculo e com hífens (8-4-4-4-12)
    value.len() == 36
        && value.char_indices().all(|(i, c)| match i {
            8 | 13 | 18 | 23 => c == '-',
            _ => c.is_ascii_digit() || ('a'..='f').contains(&c),
        })
}

fn is_event_type(value: &str) -> bool {
    // ^[a-z]+(\.[a-z]+)+$
    let parts: Vec<&str> = value.split('.').collect();
    value.len() <= 100
        && parts.len() >= 2
        && parts
            .iter()
            .all(|p| !p.is_empty() && p.chars().all(|c| c.is_ascii_lowercase()))
}

pub fn is_correlation_id(value: &str) -> bool {
    (1..=64).contains(&value.len())
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
}

pub fn is_item_id(value: &str) -> bool {
    (1..=64).contains(&value.len())
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-'))
}

impl Envelope {
    pub fn parse(body: &[u8]) -> Result<Self, EnvelopeError> {
        let envelope: Envelope =
            serde_json::from_slice(body).map_err(|e| EnvelopeError::Json(e.to_string()))?;
        envelope.validate()?;
        Ok(envelope)
    }

    pub fn validate(&self) -> Result<(), EnvelopeError> {
        if !is_uuid(&self.event_id) {
            return Err(EnvelopeError::Field("event_id"));
        }
        if !is_event_type(&self.event_type) {
            return Err(EnvelopeError::Field("event_type"));
        }
        if self.version < 1 {
            return Err(EnvelopeError::Field("version"));
        }
        if self.producer.is_empty() || self.producer.len() > 50 {
            return Err(EnvelopeError::Field("producer"));
        }
        if !is_correlation_id(&self.correlation_id) {
            return Err(EnvelopeError::Field("correlation_id"));
        }
        if self.job_id.as_deref().is_some_and(|id| !is_uuid(id)) {
            return Err(EnvelopeError::Field("job_id"));
        }
        if !self.payload.is_object() {
            return Err(EnvelopeError::Field("payload"));
        }
        Ok(())
    }

    /// Evento de resultado com id determinístico: reprocessar o mesmo pedido gera o
    /// mesmo event_id, e o inbox da API (processed_event) descarta a duplicata.
    pub fn result_for(request: &Envelope, event_type: &str, payload: Value) -> Envelope {
        let name = format!("{}:{}:v1", request.event_id, event_type);
        Envelope {
            event_id: Uuid::new_v5(&RESULT_NAMESPACE, name.as_bytes()).to_string(),
            event_type: event_type.to_string(),
            version: 1,
            occurred_at: Utc::now(),
            producer: PRODUCER.to_string(),
            correlation_id: request.correlation_id.clone(),
            job_id: request.job_id.clone(),
            payload,
        }
    }

    pub fn to_json(&self) -> Vec<u8> {
        // occurred_at em RFC 3339 com Z, como no Python e no Go
        let mut value = serde_json::to_value(self).expect("envelope serializável");
        value["occurred_at"] = Value::String(
            self.occurred_at
                .to_rfc3339_opts(SecondsFormat::Millis, true),
        );
        serde_json::to_vec(&value).expect("envelope serializável")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ItemKind {
    Text,
    Choice,
    Number,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluationItemV1 {
    pub item_id: String,
    pub kind: ItemKind,
    pub answer: Vec<String>,
    pub expected: Vec<String>,
    #[serde(default = "default_true")]
    pub ignore_case: bool,
    #[serde(default)]
    pub ignore_accents: bool,
    #[serde(default)]
    pub max_typos: u8,
    #[serde(default)]
    pub tolerance: f64,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluationRequestedV1 {
    pub evaluation_id: String,
    pub items: Vec<EvaluationItemV1>,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluationItemResultV1 {
    pub item_id: String,
    pub correct: bool,
    pub score: f64,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluationCompletedV1 {
    pub evaluation_id: String,
    pub total_items: usize,
    pub correct_items: usize,
    pub score: f64,
    pub items: Vec<EvaluationItemResultV1>,
    pub engine: String,
    pub engine_version: String,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluationFailedV1 {
    pub evaluation_id: String,
    pub error_code: String,
    #[serde(default)]
    pub error_message: String,
    #[serde(default)]
    pub retryable: bool,
}

/// Regras do contrato que o serde sozinho não garante. Erro = pedido inválido
/// (vira `evaluation.failed` com `invalid_request`, sem retry).
pub fn validate_request(request: &EvaluationRequestedV1) -> Result<(), String> {
    if !is_uuid(&request.evaluation_id) {
        return Err("evaluation_id inválido".into());
    }
    if request.items.is_empty() || request.items.len() > MAX_ITEMS {
        return Err(format!("items precisa ter de 1 a {MAX_ITEMS} itens"));
    }
    let mut seen = std::collections::HashSet::new();
    for item in &request.items {
        let id = &item.item_id;
        if !is_item_id(id) {
            return Err("item_id inválido".into());
        }
        if !seen.insert(id.as_str()) {
            return Err(format!("item {id}: item_id repetido"));
        }
        if item.answer.len() > MAX_VALUES {
            return Err(format!(
                "item {id}: answer com mais de {MAX_VALUES} valores"
            ));
        }
        if item.expected.is_empty() || item.expected.len() > MAX_VALUES {
            return Err(format!(
                "item {id}: expected precisa ter de 1 a {MAX_VALUES} valores"
            ));
        }
        if item
            .answer
            .iter()
            .chain(item.expected.iter())
            .any(|v| v.chars().count() > MAX_TEXT_CHARS)
        {
            return Err(format!(
                "item {id}: texto com mais de {MAX_TEXT_CHARS} caracteres"
            ));
        }
        if item.max_typos > MAX_TYPOS {
            return Err(format!("item {id}: max_typos acima de {MAX_TYPOS}"));
        }
        if !item.tolerance.is_finite() || item.tolerance < 0.0 {
            return Err(format!("item {id}: tolerance inválida"));
        }
        match item.kind {
            ItemKind::Text | ItemKind::Number if item.answer.len() != 1 => {
                return Err(format!("item {id}: answer precisa ter exatamente 1 valor"));
            }
            ItemKind::Number
                if item
                    .expected
                    .iter()
                    .any(|e| crate::evaluate::parse_number(e).is_none()) =>
            {
                return Err(format!("item {id}: gabarito numérico inválido"));
            }
            _ => {}
        }
    }
    Ok(())
}
