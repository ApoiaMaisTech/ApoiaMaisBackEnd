//! `/healthz` (processo vivo) e `/readyz` (consumindo do RabbitMQ), só na rede interna.
//! Servidor HTTP mínimo: duas rotas, sem dependência a mais.

use std::io::{Read, Write};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

fn response(path: &str, ready: bool) -> (u16, &'static str) {
    match path {
        "/healthz" => (200, "ok"),
        "/readyz" if ready => (200, "ready"),
        "/readyz" => (503, "not ready"),
        _ => (404, "not found"),
    }
}

pub async fn serve(addr: String, ready: Arc<AtomicBool>) -> std::io::Result<()> {
    let listener = TcpListener::bind(&addr).await?;
    tracing::info!(addr = %addr, "health server");
    loop {
        let (mut socket, _) = listener.accept().await?;
        let ready = ready.clone();
        tokio::spawn(async move {
            let mut buf = [0u8; 1024];
            let Ok(Ok(n)) =
                tokio::time::timeout(Duration::from_secs(2), socket.read(&mut buf)).await
            else {
                return;
            };
            let request = String::from_utf8_lossy(&buf[..n]);
            let path = request.split_whitespace().nth(1).unwrap_or("/");
            let (status, body) = response(path, ready.load(Ordering::SeqCst));
            let reason = match status {
                200 => "OK",
                503 => "Service Unavailable",
                _ => "Not Found",
            };
            let reply = format!(
                "HTTP/1.1 {status} {reason}\r\ncontent-type: text/plain\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{body}",
                body.len()
            );
            let _ = socket.write_all(reply.as_bytes()).await;
        });
    }
}

/// Usado pelo HEALTHCHECK do Docker (imagem sem shell nem curl).
pub fn check(addr: &str) -> bool {
    let port = addr.rsplit(':').next().unwrap_or("8082");
    let Ok(mut stream) = std::net::TcpStream::connect(format!("127.0.0.1:{port}")) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(3)));
    if stream
        .write_all(b"GET /readyz HTTP/1.1\r\nhost: localhost\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut buf = [0u8; 64];
    let n = stream.read(&mut buf).unwrap_or(0);
    String::from_utf8_lossy(&buf[..n]).starts_with("HTTP/1.1 200")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rotas() {
        assert_eq!(response("/healthz", false).0, 200);
        assert_eq!(response("/readyz", true).0, 200);
        assert_eq!(response("/readyz", false).0, 503);
        assert_eq!(response("/x", true).0, 404);
    }
}
