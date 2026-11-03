import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"mysql+aiomysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/"
    f"{os.getenv('DB_NAME', 'ApoiaMaisDB')}"
)

# Pool de conexões por processo. Sem pool (NullPool) cada requisição abria uma conexão
# nova com o MySQL: ~7 ms a mais por requisição (docs/PERFORMANCE.md).
# DB_POOL_SIZE=0 volta ao NullPool (usado nos testes: o TestClient abre um event loop por
# requisição e conexão de pool fica presa ao loop em que nasceu).
# Conexões no MySQL = (DB_POOL_SIZE + DB_MAX_OVERFLOW) x processos; o padrão do MySQL é 151.
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))


def pool_options(pool_size: int = DB_POOL_SIZE) -> dict:
    if pool_size <= 0:
        return {"poolclass": NullPool}
    return {
        "pool_size": pool_size,
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": float(os.getenv("DB_POOL_TIMEOUT_SECONDS", "10")),
        # abaixo do wait_timeout do MySQL (8 h). Sem pool_pre_ping: com SQLAlchemy 2.0.31 +
        # aiomysql 0.2.0 o ping falha (TypeError em ping(reconnect)). Conexão derrubada
        # (restart do MySQL) é invalidada pelo SQLAlchemy no primeiro erro de desconexão.
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
    }


def build_engine(url: str = DATABASE_URL, pool_size: int = DB_POOL_SIZE):
    return create_async_engine(
        url,
        # SQL no log só quando pedido: em produção vaza dados e polui os logs
        echo=os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes"),
        # LGPD: mensagens de erro do SQLAlchemy não carregam os valores (email, hash, nome...)
        hide_parameters=True,
        **pool_options(pool_size),
    )


engine = build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)