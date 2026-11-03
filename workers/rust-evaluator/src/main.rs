use std::process::ExitCode;
use std::sync::Arc;
use std::sync::atomic::AtomicBool;

use rust_evaluator::{broker, config::Config, health};
use tokio::sync::watch;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> ExitCode {
    if std::env::args().nth(1).as_deref() == Some("healthcheck") {
        let addr = std::env::var("HEALTH_ADDR").unwrap_or_else(|_| "0.0.0.0:8082".into());
        return if health::check(&addr) {
            ExitCode::SUCCESS
        } else {
            ExitCode::FAILURE
        };
    }

    // logs JSON com correlation_id/event_id; nunca o conteúdo das respostas (LGPD)
    tracing_subscriber::fmt()
        .json()
        .flatten_event(true)
        .with_current_span(true)
        .with_span_list(false)
        .with_env_filter(
            EnvFilter::try_from_env("LOG_LEVEL")
                .unwrap_or_else(|_| EnvFilter::new("info,lapin=warn")),
        )
        .init();

    let cfg = match Config::from_env() {
        Ok(cfg) => cfg,
        Err(err) => {
            tracing::error!(error = %err, "configuração inválida");
            return ExitCode::from(2);
        }
    };

    let ready = Arc::new(AtomicBool::new(false));
    let (stop_tx, stop_rx) = watch::channel(false);

    let health_addr = cfg.health_addr.clone();
    let health_ready = ready.clone();
    tokio::spawn(async move {
        if let Err(err) = health::serve(health_addr, health_ready).await {
            tracing::error!(error = %err, "health server parou");
        }
    });

    tokio::spawn(async move {
        let mut term = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("handler de SIGTERM");
        tokio::select! {
            _ = term.recv() => {}
            _ = tokio::signal::ctrl_c() => {}
        }
        tracing::info!("sinal de encerramento recebido");
        let _ = stop_tx.send(true);
    });

    tracing::info!(queue = %cfg.queue, prefetch = cfg.prefetch, version = env!("CARGO_PKG_VERSION"), "rust-evaluator iniciado");
    broker::run(cfg, stop_rx, ready).await;
    tracing::info!("rust-evaluator encerrado");
    ExitCode::SUCCESS
}
