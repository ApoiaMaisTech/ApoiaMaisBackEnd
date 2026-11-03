//! Topologia do RabbitMQ espelhada de `app/infrastructure/messaging/topology.py`
//! e `workers/go-worker/internal/broker/topology.go`. Os argumentos precisam ser
//! idênticos nos três (senão o RabbitMQ responde PRECONDITION_FAILED).

pub const EVENTS_EXCHANGE: &str = "apoiamais.events";
pub const RETRY_EXCHANGE: &str = "apoiamais.retry";
pub const DLX_EXCHANGE: &str = "apoiamais.dlx";
pub const UNROUTED_EXCHANGE: &str = "apoiamais.unrouted";
pub const UNROUTED_QUEUE: &str = "apoiamais.unrouted";

pub const DELIVERY_LIMIT: i32 = 10;
pub const RETRY_DELAYS_MS: [i32; 3] = [10_000, 60_000, 300_000];

pub const RETRY_COUNT_HEADER: &str = "x-retry-count";
pub const ERROR_HEADER: &str = "x-last-error";

pub fn retry_queue_name(queue: &str, delay_ms: i32) -> String {
    format!("{queue}.retry.{delay_ms}")
}

pub fn dlq_name(queue: &str) -> String {
    format!("{queue}.dlq")
}

/// `attempt` começa em 1; depois da última faixa, repete a maior.
pub fn retry_delay_for(attempt: u32) -> i32 {
    let index = (attempt.max(1) as usize).min(RETRY_DELAYS_MS.len()) - 1;
    RETRY_DELAYS_MS[index]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nomes_iguais_aos_do_python_e_do_go() {
        assert_eq!(retry_queue_name("q", 10_000), "q.retry.10000");
        assert_eq!(dlq_name("q"), "q.dlq");
    }

    #[test]
    fn atraso_do_retry_por_tentativa() {
        assert_eq!(retry_delay_for(0), 10_000);
        assert_eq!(retry_delay_for(1), 10_000);
        assert_eq!(retry_delay_for(2), 60_000);
        assert_eq!(retry_delay_for(3), 300_000);
        assert_eq!(retry_delay_for(9), 300_000);
    }
}
