"""Política de retenção (LGPD, art. 15 e 16): apaga o que já cumpriu a finalidade.

| tabela            | o que sai                        | prazo padrão | por quê |
|-------------------|----------------------------------|--------------|---------|
| processed_event   | eventos já consumidos            | 30 dias      | só servem para deduplicar reentregas (retry, DLQ) |
| outbox_event      | eventos já publicados            | 7 dias       | só servem para diagnóstico do relay |
| log_error         | erros registrados                | 90 dias      | diagnóstico |
| notification      | notificações já lidas            | 180 dias     | o usuário já viu |
| login_acao        | trilha de auditoria (ip, agente) | 180 dias     | Marco Civil (art. 15) exige guardar registros de acesso por 6 meses: o prazo nunca fica abaixo disso |

Os dados de conta, de paciente e clínicos não têm prazo automático: saem quando a
conta/paciente é excluído (as FKs são CASCADE; ver docs/LGPD.md).
Apaga em lotes para não segurar locks longos no MySQL.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger("apoiamais.retention")

# Marco Civil da Internet, art. 15: registros de acesso a aplicações por 6 meses
MIN_AUDIT_DAYS = 180


@dataclass(frozen=True)
class RetentionPolicy:
    processed_event_days: int = 30
    outbox_published_days: int = 7
    error_log_days: int = 90
    read_notification_days: int = 180
    audit_log_days: int = MIN_AUDIT_DAYS

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if value < 1:
                raise ValueError(f"{name} precisa ser >= 1")
        if self.audit_log_days < MIN_AUDIT_DAYS:
            raise ValueError(f"audit_log_days não pode ser menor que {MIN_AUDIT_DAYS} (Marco Civil, art. 15)")


# (nome, tabela, coluna de data, filtro extra, atributo da política). Tudo fixo no código:
# nada aqui vem de entrada externa, então montar o SQL com f-string é seguro.
_RULES = (
    ("processed_event", "processed_event", "processed_at", "", "processed_event_days"),
    ("outbox_event", "outbox_event", "published_at", "AND published_at IS NOT NULL", "outbox_published_days"),
    ("log_error", "log_error", "created_at", "", "error_log_days"),
    ("notification", "notification", "created_at", "AND `read` = 1", "read_notification_days"),
    ("login_acao", "login_acao", "created_at", "", "audit_log_days"),
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def apply_retention(
    session_factory: async_sessionmaker,
    policy: RetentionPolicy | None = None,
    now: datetime | None = None,
    batch_size: int = 1000,
) -> dict[str, int]:
    policy = policy or RetentionPolicy()
    now = now or _utcnow()
    removed: dict[str, int] = {}

    for name, table, column, extra, attr in _RULES:
        cutoff = now - timedelta(days=getattr(policy, attr))
        statement = text(f"DELETE FROM `{table}` WHERE `{column}` < :cutoff {extra} LIMIT :batch")
        total = 0
        while True:
            async with session_factory() as session:
                async with session.begin():
                    result = await session.execute(statement, {"cutoff": cutoff, "batch": batch_size})
            total += result.rowcount or 0
            if (result.rowcount or 0) < batch_size:
                break
        removed[name] = total

    logger.info("retenção aplicada", extra={"removed": removed})
    return removed
