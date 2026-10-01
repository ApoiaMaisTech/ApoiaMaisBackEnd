import pytest

from app.infrastructure.rate_limit import (
    InMemoryRateLimitStorage,
    Rate,
    RateLimiter,
    parse_rate,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("5/minute", Rate(5, 60)),
        ("100/hour", Rate(100, 3600)),
        (" 1/second ", Rate(1, 1)),
        ("10/Day", Rate(10, 86400)),
    ],
)
def test_parse_rate(value, expected):
    assert parse_rate(value) == expected


@pytest.mark.parametrize("value", ["", "5", "cinco/minute", "5/semana", "0/minute", "-1/minute"])
def test_parse_rate_invalido(value):
    with pytest.raises(ValueError):
        parse_rate(value)


@pytest.mark.asyncio
async def test_memoria_conta_por_chave():
    limiter = RateLimiter(InMemoryRateLimitStorage())
    rate = Rate(2, 60)

    assert (await limiter.hit("a", rate)).allowed
    assert (await limiter.hit("a", rate)).allowed
    bloqueado = await limiter.hit("a", rate)
    outra_chave = await limiter.hit("b", rate)

    assert not bloqueado.allowed
    assert 0 < bloqueado.retry_after <= 60
    assert outra_chave.allowed


@pytest.mark.asyncio
async def test_janela_expirada_zera_contador(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr("app.infrastructure.rate_limit.time.monotonic", lambda: agora[0])
    limiter = RateLimiter(InMemoryRateLimitStorage())
    rate = Rate(1, 60)

    assert (await limiter.hit("a", rate)).allowed
    assert not (await limiter.hit("a", rate)).allowed

    agora[0] += 61

    assert (await limiter.hit("a", rate)).allowed


@pytest.mark.asyncio
async def test_storage_fora_do_ar_usa_fallback_em_memoria():
    class RedisQuebrado:
        async def hit(self, key, window_seconds):
            raise ConnectionError("redis fora")

        def reset(self):
            pass

    limiter = RateLimiter(RedisQuebrado())
    rate = Rate(1, 60)

    assert (await limiter.hit("a", rate)).allowed
    assert not (await limiter.hit("a", rate)).allowed
