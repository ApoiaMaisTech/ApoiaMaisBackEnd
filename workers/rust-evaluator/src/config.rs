//! Configuração por variáveis de ambiente (ver README.md).

use std::time::Duration;

#[derive(Clone, Debug)]
pub struct Config {
    pub amqp_url: String,
    pub queue: String,
    pub prefetch: u16,
    pub max_retries: u32,
    pub max_message_bytes: usize,
    pub drain_timeout: Duration,
    pub health_addr: String,
}

pub const DEFAULT_QUEUE: &str = "rust-evaluator.evaluation";

impl Config {
    pub fn from_env() -> Result<Self, String> {
        let amqp_url =
            std::env::var("AMQP_URL").map_err(|_| "AMQP_URL é obrigatório".to_string())?;
        if amqp_url.trim().is_empty() {
            return Err("AMQP_URL é obrigatório".into());
        }
        Ok(Self {
            amqp_url: normalize_amqp_url(&amqp_url),
            queue: env_or("EVALUATOR_QUEUE", DEFAULT_QUEUE.to_string())?,
            prefetch: env_or("PREFETCH", 16u16)?.max(1),
            max_retries: env_or("MAX_RETRIES", 3u32)?,
            max_message_bytes: env_or("MAX_MESSAGE_BYTES", 256 * 1024usize)?,
            drain_timeout: Duration::from_secs(env_or("DRAIN_TIMEOUT_SECONDS", 15u64)?),
            health_addr: env_or("HEALTH_ADDR", "0.0.0.0:8082".to_string())?,
        })
    }
}

/// `amqp://host:5672/` (barra final, sem vhost) é o vhost "/" no Python (aio-pika) e no Go
/// (amqp091), mas pela especificação de URI do AMQP é o vhost vazio, e o lapin segue a
/// especificação ("vhost not found"). Como o compose usa a mesma URL para os três,
/// normalizamos aqui: caminho vazio ou só "/" vira "%2f".
pub fn normalize_amqp_url(url: &str) -> String {
    let url = url.trim();
    let Some(scheme_end) = url.find("://") else {
        return url.to_string();
    };
    let rest = &url[scheme_end + 3..];
    let (authority_and_path, query) = match rest.find('?') {
        Some(i) => (&rest[..i], &rest[i..]),
        None => (rest, ""),
    };
    let path = authority_and_path
        .find('/')
        .map(|i| &authority_and_path[i..]);
    let base = &url[..scheme_end + 3];
    match path {
        None => format!("{base}{authority_and_path}/%2f{query}"),
        Some("/") => format!("{base}{}%2f{query}", authority_and_path),
        Some(_) => url.to_string(),
    }
}

fn env_or<T: std::str::FromStr>(name: &str, default: T) -> Result<T, String> {
    match std::env::var(name) {
        Ok(value) if !value.trim().is_empty() => value
            .trim()
            .parse()
            .map_err(|_| format!("{name} inválido: {value:?}")),
        _ => Ok(default),
    }
}

#[cfg(test)]
mod tests {
    use super::normalize_amqp_url;

    #[test]
    fn url_sem_vhost_usa_o_vhost_padrao() {
        assert_eq!(
            normalize_amqp_url("amqp://u:p@rabbitmq:5672/"),
            "amqp://u:p@rabbitmq:5672/%2f"
        );
        assert_eq!(
            normalize_amqp_url("amqp://u:p@rabbitmq:5672"),
            "amqp://u:p@rabbitmq:5672/%2f"
        );
        assert_eq!(
            normalize_amqp_url("amqp://u:p@rabbitmq:5672/?heartbeat=30"),
            "amqp://u:p@rabbitmq:5672/%2f?heartbeat=30"
        );
    }

    #[test]
    fn vhost_explicito_e_mantido() {
        assert_eq!(
            normalize_amqp_url("amqp://u:p@h:5672/%2f"),
            "amqp://u:p@h:5672/%2f"
        );
        assert_eq!(
            normalize_amqp_url("amqp://u:p@h:5672/apoiamais"),
            "amqp://u:p@h:5672/apoiamais"
        );
    }
}
