"""Aplica a política de retenção de dados (LGPD) uma vez e mostra quanto foi removido.

Uso:
    python -m scripts.aplicar_retencao
    docker compose run --rm api-worker python -m scripts.aplicar_retencao

O api-worker já aplica a política sozinho a cada RETENTION_INTERVAL_HOURS; este
script serve para rodar sob demanda (ou por cron, se o worker não estiver no ar).
Prazos: variáveis RETENTION_* do .env (ver app/infrastructure/database/retention.py).
"""
import asyncio
import json

from app.core.config import settings
from app.infrastructure.database.retention import apply_retention
from app.infrastructure.database.session import AsyncSessionLocal


async def main() -> None:
    removed = await apply_retention(AsyncSessionLocal, settings.retention_policy)
    print(json.dumps(removed, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
