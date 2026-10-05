from fastapi import HTTPException, Request, Response, status

from app.api.dependencies.services import get_jwt_service
from app.core.config import settings
from app.infrastructure.rate_limit import build_rate_limiter, parse_rate

rate_limiter = build_rate_limiter(settings.REDIS_URL)


def _client_ip(request: Request) -> str:
    # atrás de proxy, o uvicorn com --proxy-headers já reescreve request.client
    return request.client.host if request.client else "unknown"


def _client_identity(request: Request) -> str:
    # No hospital vários tablets saem pelo mesmo IP (NAT): com token válido o
    # limite é por usuário; sem token (ou token inválido) cai no IP.
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            payload = get_jwt_service().verify_token(token)
            user_id = payload.get("user_id")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return f"ip:{_client_ip(request)}"


# dependência por rota: rate_limit("login", settings.RATE_LIMIT_LOGIN)
# per_user=False força o limite por IP (login: ainda não há usuário)
def rate_limit(scope: str, rate: str, per_user: bool = True):
    parsed = parse_rate(rate)

    async def dependency(request: Request, response: Response) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        identity = _client_identity(request) if per_user else f"ip:{_client_ip(request)}"
        result = await rate_limiter.hit(f"{scope}:{identity}", parsed)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições. Tente novamente mais tarde.",
                headers={"Retry-After": str(result.retry_after)},
            )
        response.headers["X-RateLimit-Limit"] = str(parsed.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)

    return dependency
