from fastapi import HTTPException, Request, Response, status

from app.core.config import settings
from app.infrastructure.rate_limit import build_rate_limiter, parse_rate

rate_limiter = build_rate_limiter(settings.REDIS_URL)


def _client_ip(request: Request) -> str:
    # atrás de proxy, o uvicorn com --proxy-headers já reescreve request.client
    return request.client.host if request.client else "unknown"


# dependência por rota: rate_limit("login", settings.RATE_LIMIT_LOGIN)
def rate_limit(scope: str, rate: str):
    parsed = parse_rate(rate)

    async def dependency(request: Request, response: Response) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        result = await rate_limiter.hit(f"{scope}:{_client_ip(request)}", parsed)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições. Tente novamente mais tarde.",
                headers={"Retry-After": str(result.retry_after)},
            )
        response.headers["X-RateLimit-Limit"] = str(parsed.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)

    return dependency
