"""Worker da API: publica o outbox no RabbitMQ e consome os resultados dos jobs
(ilustrações do go-worker e avaliações do rust-evaluator).

Roda na mesma imagem da API, como outro processo:
    python -m app.worker               # executa
    python -m app.worker --healthcheck # usado pelo HEALTHCHECK do compose

A API (uvicorn) não abre conexão com o RabbitMQ: só grava no outbox. Assim uma
queda do broker não derruba requisições, e os eventos saem quando ele voltar.
"""
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.database.retention import apply_retention
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.messaging.consumer import EventConsumer
from app.infrastructure.messaging.handlers.ai_image_results import QUEUE_NAME, AiImageResultHandlers
from app.infrastructure.messaging.handlers.evaluation_results import (
    QUEUE_NAME as EVALUATION_QUEUE_NAME,
    EvaluationResultHandlers,
)
from app.infrastructure.messaging.outbox import OutboxRelay
from app.infrastructure.messaging.publisher import RabbitPublisher

logger = logging.getLogger("apoiamais.worker")

HEARTBEAT_FILE = Path("/tmp/apoiamais-worker.heartbeat")
HEARTBEAT_MAX_AGE_SECONDS = 60


def healthcheck() -> int:
    try:
        age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    except FileNotFoundError:
        return 1
    return 0 if age < HEARTBEAT_MAX_AGE_SECONDS else 1


async def _maybe_apply_retention(last_run: float | None) -> float | None:
    """Aplica a retenção (LGPD) no máximo a cada RETENTION_INTERVAL_HOURS. Erro não derruba o worker."""
    if not settings.RETENTION_ENABLED:
        return last_run
    now = time.monotonic()
    if last_run is not None and now - last_run < settings.RETENTION_INTERVAL_HOURS * 3600:
        return last_run
    try:
        await apply_retention(AsyncSessionLocal, settings.retention_policy)
    except Exception:
        logger.exception("erro ao aplicar a retenção de dados")
    return now


async def _relay_loop(relay: OutboxRelay, consumers: list[EventConsumer], stop: asyncio.Event) -> None:
    last_retention: float | None = None
    while not stop.is_set():
        last_retention = await _maybe_apply_retention(last_retention)
        try:
            published = await relay.run_once()
            # só se declara vivo se o banco respondeu e todos os consumidores estão conectados
            if all(consumer.is_connected for consumer in consumers):
                HEARTBEAT_FILE.touch()
            if published:
                continue  # ainda pode haver fila no outbox
        except Exception:
            logger.exception("erro no relay do outbox")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.OUTBOX_POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass


async def run() -> None:
    if not settings.RABBITMQ_URL:
        raise SystemExit("RABBITMQ_URL é obrigatório para o worker")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    publisher = RabbitPublisher(settings.RABBITMQ_URL)
    await publisher.connect()

    consumers = [
        EventConsumer(
            settings.RABBITMQ_URL,
            queue_name,
            handlers,
            max_retries=settings.MESSAGING_MAX_RETRIES,
            prefetch=settings.MESSAGING_PREFETCH,
        )
        for queue_name, handlers in (
            (QUEUE_NAME, AiImageResultHandlers(AsyncSessionLocal).handlers()),
            (EVALUATION_QUEUE_NAME, EvaluationResultHandlers(AsyncSessionLocal).handlers()),
        )
    ]
    consumer_tasks = [asyncio.create_task(consumer.run(stop)) for consumer in consumers]

    relay = OutboxRelay(AsyncSessionLocal, publisher, batch_size=settings.OUTBOX_BATCH_SIZE)
    logger.info("worker iniciado")
    try:
        await _relay_loop(relay, consumers, stop)
    finally:
        logger.info("encerrando worker")
        stop.set()
        await asyncio.gather(*consumer_tasks)
        await publisher.close()


def main() -> None:
    if "--healthcheck" in sys.argv:
        sys.exit(healthcheck())
    configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)
    asyncio.run(run())


if __name__ == "__main__":
    main()
