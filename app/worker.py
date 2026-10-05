"""Worker da API: publica o outbox no RabbitMQ e consome os resultados dos jobs.

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
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.messaging.consumer import EventConsumer
from app.infrastructure.messaging.handlers.ai_image_results import QUEUE_NAME, AiImageResultHandlers
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


async def _relay_loop(relay: OutboxRelay, consumer: EventConsumer, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            published = await relay.run_once()
            # só se declara vivo se o banco respondeu e o consumidor está conectado
            if consumer.is_connected:
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

    consumer = EventConsumer(
        settings.RABBITMQ_URL,
        QUEUE_NAME,
        AiImageResultHandlers(AsyncSessionLocal).handlers(),
        max_retries=settings.MESSAGING_MAX_RETRIES,
        prefetch=settings.MESSAGING_PREFETCH,
    )
    consumer_task = asyncio.create_task(consumer.run(stop))

    relay = OutboxRelay(AsyncSessionLocal, publisher, batch_size=settings.OUTBOX_BATCH_SIZE)
    logger.info("worker iniciado")
    try:
        await _relay_loop(relay, consumer, stop)
    finally:
        logger.info("encerrando worker")
        stop.set()
        await consumer_task
        await publisher.close()


def main() -> None:
    if "--healthcheck" in sys.argv:
        sys.exit(healthcheck())
    configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)
    asyncio.run(run())


if __name__ == "__main__":
    main()
