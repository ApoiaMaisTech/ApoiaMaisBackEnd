"""Lista ou reprocessa a DLQ de uma fila do RabbitMQ (depois de corrigir a causa).

Uso:
    python -m scripts.reprocessar_dlq --fila apoiamais-api.ai-image-results --listar
    python -m scripts.reprocessar_dlq --fila apoiamais-api.ai-image-results
    python -m scripts.reprocessar_dlq --fila go-worker.ai-image --limite 10 --tipo ai.image.requested

No compose: docker compose run --rm api-worker python -m scripts.reprocessar_dlq --fila ...

As mensagens voltam para a fila com o contador de tentativas zerado. Uma
mensagem reprocessada mais de --max-reprocessamentos vezes fica na DLQ.
Detalhes e garantias: app/infrastructure/messaging/dlq.py.
"""
import argparse
import asyncio
import sys

from app.core.config import settings
from app.infrastructure.messaging.dlq import list_dlq, replay_dlq


def _args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fila", required=True, help="fila de origem (a DLQ é <fila>.dlq)")
    parser.add_argument("--listar", action="store_true", help="só mostra as mensagens, sem remover")
    parser.add_argument("--limite", type=int, default=None, help="máximo de mensagens")
    parser.add_argument("--tipo", default=None, help="só reprocessa este event_type")
    parser.add_argument("--max-reprocessamentos", type=int, default=3)
    return parser.parse_args(argv)


async def main(argv: list[str]) -> int:
    args = _args(argv)
    if not settings.RABBITMQ_URL:
        print("RABBITMQ_URL não definido", file=sys.stderr)
        return 2

    if args.listar:
        total, messages = await list_dlq(settings.RABBITMQ_URL, args.fila, limit=args.limite or 20)
        print(f"{total} mensagem(ns) em {args.fila}.dlq")
        for m in messages:
            print(
                f"- {m.message_id} {m.event_type} correlation_id={m.correlation_id} "
                f"tentativas={m.retry_count} reprocessamentos={m.replay_count} erro={m.last_error!r}"
            )
        return 0

    result = await replay_dlq(
        settings.RABBITMQ_URL,
        args.fila,
        limit=args.limite,
        event_type=args.tipo,
        max_replays=args.max_reprocessamentos,
    )
    print(f"reprocessadas={result.replayed} mantidas_na_dlq={result.kept} falhas={result.failed}")
    return 1 if result.failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
