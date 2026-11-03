//! rust-evaluator: avalia atividades do ApoiaMais de forma determinística.
//!
//! Consome `evaluation.requested` v1 do RabbitMQ e publica `evaluation.completed`
//! ou `evaluation.failed` v1. Não acessa banco: entrada e saída são eventos, e a
//! API (FastAPI) é a dona dos dados. Contratos em `contracts/events/`.

pub mod broker;
pub mod config;
pub mod evaluate;
pub mod events;
pub mod handler;
pub mod health;
pub mod topology;
