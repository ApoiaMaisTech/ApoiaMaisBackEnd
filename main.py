import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.ai_images import router as ai_images_router
from app.api.exception_handlers import register_exception_handlers
from app.api.dependencies.rate_limit import rate_limit
from app.api.middleware.correlation import CorrelationIdMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.database.session import AsyncSessionLocal

configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)
logger = logging.getLogger("apoiamais")


# Sem ENABLE_DOCS, /docs, /redoc e /openapi.json não existem (404): o mapa de
# rotas não fica público. O contrato continua sendo exportado pelo CI
# (scripts/exportar_openapi.py usa app.openapi(), que não depende dessas rotas).
app = FastAPI(
    title="ApoiaMais API",
    version="1.0.0",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
    expose_headers=["Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Correlation-ID"],
)
# por último = mais externo: o correlation_id já existe quando qualquer outra coisa loga
app.add_middleware(CorrelationIdMiddleware)

# limite geral por usuário (ou IP, sem token); rotas sensíveis têm limites próprios mais baixos
default_rate_limit = [Depends(rate_limit("default", settings.RATE_LIMIT_DEFAULT))]

app.include_router(users_router, prefix="/api/users", tags=["Users"], dependencies=default_rate_limit)
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"], dependencies=default_rate_limit)
app.include_router(ai_images_router, prefix="/api", tags=["AI Images"], dependencies=default_rate_limit)


@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "ApoiaMais API"}


# liveness: o processo responde (sem tocar em dependências)
@app.get("/health/live", include_in_schema=False)
async def liveness():
    return {"status": "alive"}


# readiness: pode receber tráfego (banco acessível). Sem detalhes do erro na resposta.
@app.get("/health/ready", include_in_schema=False)
@app.get("/health", include_in_schema=False)
async def readiness():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Health check: banco indisponível", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unavailable"},
        )
    return {"status": "healthy", "database": "connected"}
