import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("apoiamais.rate_limit")

_WINDOWS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass(frozen=True)
class Rate:
    limit: int
    window_seconds: int


def parse_rate(value: str) -> Rate:
    # formato "5/minute", "100/hour"...
    try:
        limit, unit = value.strip().split("/", 1)
        rate = Rate(limit=int(limit), window_seconds=_WINDOWS[unit.strip().lower()])
    except (ValueError, KeyError):
        raise ValueError(f"Rate limit inválido: {value!r} (use por exemplo '5/minute')")
    if rate.limit <= 0:
        raise ValueError(f"Rate limit inválido: {value!r} (o limite deve ser positivo)")
    return rate


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


# janela fixa em memória: só serve com um processo (dev, testes)
class InMemoryRateLimitStorage:
    def __init__(self):
        self._hits: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, window_seconds: int) -> tuple[int, int]:
        now = time.monotonic()
        count, reset_at = self._hits.get(key, (0, 0.0))
        if reset_at <= now:
            count, reset_at = 0, now + window_seconds
            if len(self._hits) > 10_000:
                self._hits = {k: v for k, v in self._hits.items() if v[1] > now}
        count += 1
        self._hits[key] = (count, reset_at)
        return count, max(1, int(reset_at - now + 0.999))

    def reset(self) -> None:
        self._hits.clear()


# janela fixa no Redis: contador compartilhado entre processos e réplicas
class RedisRateLimitStorage:
    def __init__(self, url: str):
        from redis.asyncio import Redis

        self._redis = Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)

    async def hit(self, key: str, window_seconds: int) -> tuple[int, int]:
        redis_key = f"ratelimit:{key}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds, nx=True)
            pipe.ttl(redis_key)
            count, _, ttl = await pipe.execute()
        return int(count), max(1, int(ttl))

    def reset(self) -> None:
        pass


class RateLimiter:
    def __init__(self, storage, fallback: InMemoryRateLimitStorage | None = None):
        self.storage = storage
        self.fallback = fallback or InMemoryRateLimitStorage()

    async def hit(self, key: str, rate: Rate) -> RateLimitResult:
        try:
            count, ttl = await self.storage.hit(key, rate.window_seconds)
        except Exception:
            # Redis fora do ar não pode derrubar a API: limita por processo até ele voltar
            logger.warning("Rate limit sem Redis, usando memória local", exc_info=True)
            count, ttl = await self.fallback.hit(key, rate.window_seconds)

        return RateLimitResult(
            allowed=count <= rate.limit,
            remaining=max(0, rate.limit - count),
            retry_after=ttl,
        )

    def reset(self) -> None:
        self.storage.reset()
        self.fallback.reset()


def build_rate_limiter(redis_url: str) -> RateLimiter:
    if redis_url:
        return RateLimiter(RedisRateLimitStorage(redis_url))
    return RateLimiter(InMemoryRateLimitStorage())
