import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.exception_handlers import register_exception_handlers
from app.api.dependencies.rate_limit import rate_limit
from app.core.config import settings
from app.infrastructure.database.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("apoiamais")


app = FastAPI(
    title="ApoiaMais API",
    version="1.0.0"
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# limite geral por IP; rotas sensíveis (login, cadastro) têm limites próprios mais baixos
default_rate_limit = [Depends(rate_limit("default", settings.RATE_LIMIT_DEFAULT))]

app.include_router(users_router, prefix="/api/users", tags=["Users"], dependencies=default_rate_limit)
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"], dependencies=default_rate_limit)

@app.get("/")
def read_root():
    return {"message": "ApoiaMais Backend rodando com sucesso no Docker!"}

@app.get("/health")
async def health_check():
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
