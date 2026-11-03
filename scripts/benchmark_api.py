"""Benchmark da API: latência (p50/p95/p99), vazão e erros por cenário e concorrência.

Uso (com a API rodando e RATE_LIMIT_ENABLED=false, senão o rate limit vira o gargalo):

    python -m scripts.benchmark_api --url http://127.0.0.1:8000 --pid <pid do uvicorn>
    python -m scripts.benchmark_api --concorrencia 1 10 50 --requisicoes 500 --json saida.json

O script cria no banco (mesmas variáveis DB_* da API) um professor, um aluno, um
mundo, uma fase e uma ilustração pronta, e apaga tudo no final. Com --pid, mede CPU
e memória (RSS) do processo da API durante cada cenário (Linux, via /proc).
Com --mysql-admin-url, lista as consultas mais caras (performance_schema).

Metodologia e resultados de referência: docs/PERFORMANCE.md.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from uuid import uuid4

import httpx

PASSWORD = "senha-benchmark-123"


@dataclass
class Result:
    scenario: str
    concurrency: int
    requests: int
    errors: int
    rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    cpu_percent: float | None = None
    rss_mb: float | None = None


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


class ProcSampler:
    """CPU (% de um núcleo) e RSS de um processo, lendo /proc (Linux)."""

    def __init__(self, pid: int | None):
        self.pid = pid
        self._ticks = os.sysconf("SC_CLK_TCK") if pid else 100

    def _cpu_seconds(self) -> float:
        with open(f"/proc/{self.pid}/stat") as f:
            fields = f.read().rsplit(")", 1)[1].split()
        return (int(fields[11]) + int(fields[12])) / self._ticks

    def rss_mb(self) -> float:
        with open(f"/proc/{self.pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
        return 0.0

    def start(self):
        if not self.pid:
            return None
        return time.perf_counter(), self._cpu_seconds()

    def stop(self, started) -> tuple[float | None, float | None]:
        if not self.pid or started is None:
            return None, None
        wall = time.perf_counter() - started[0]
        cpu = self._cpu_seconds() - started[1]
        return round(100 * cpu / wall, 1), round(self.rss_mb(), 1)


async def _run(client: httpx.AsyncClient, build_request, total: int, concurrency: int):
    latencies: list[float] = []
    errors = 0
    counter = iter(range(total))

    async def worker():
        nonlocal errors
        for i in counter:
            method, path, kwargs, ok = build_request(i)
            t0 = time.perf_counter()
            try:
                response = await client.request(method, path, **kwargs)
                if response.status_code not in ok:
                    errors += 1
            except httpx.HTTPError:
                errors += 1
            latencies.append((time.perf_counter() - t0) * 1000)

    started = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    return latencies, errors, time.perf_counter() - started


async def _seed():
    """Cria os dados do benchmark direto no banco. Devolve ids e um callback de limpeza."""
    import app.infrastructure.database.models  # noqa: F401
    from app.domain.entities.user import User
    from app.domain.enums.ai_image import AiImageStatus
    from app.domain.enums.user import UserRole
    from app.infrastructure.database.models.ludic.ai_image_model import AiImageModel
    from app.infrastructure.database.models.ludic.stage_model import StageModel
    from app.infrastructure.database.models.ludic.world_model import WorldModel
    from app.infrastructure.database.repositories.sql_user_repository import SqlUserRepository
    from app.infrastructure.database.session import AsyncSessionLocal
    from app.infrastructure.security.password import PasswordServiceImpl
    from sqlalchemy import delete

    password_hash = PasswordServiceImpl().hash(PASSWORD)
    tag = uuid4().hex[:8]
    teacher = User(id=uuid4(), name="Prof Benchmark", email=f"prof.{tag}@example.com", password_hash=password_hash, role=UserRole.TEACHER)
    student = User(id=uuid4(), name="Aluno Benchmark", email=f"aluno.{tag}@example.com", password_hash=password_hash, role=UserRole.STUDENT)
    world_id, stage_id, image_id = uuid4(), uuid4(), uuid4()

    async with AsyncSessionLocal() as session:
        repo = SqlUserRepository(session)
        await repo.create(teacher)
        await repo.create(student)
    async with AsyncSessionLocal() as session:
        session.add(WorldModel(id=world_id, name=f"Mundo {tag}", order=int(time.time() * 1000) % 2_000_000_000, is_active=True))
        await session.flush()
        session.add(StageModel(id=stage_id, world_id=world_id, name=f"Fase {tag}", order=1))
        await session.flush()
        # ilustração já pronta: mede o caminho comum (cache por fase), sem gerar job
        from app.domain.services.illustration_prompt import build_prompt, prompt_hash
        from app.domain.entities.ai_image import StageTheme
        from app.application.events.ai_image import storage_key_for

        prompt = build_prompt(StageTheme(stage_name=f"Fase {tag}", world_name=f"Mundo {tag}"))
        session.add(
            AiImageModel(
                id=image_id, stage_id=stage_id, requested_by_user_id=student.id,
                dedupe_key=f"{stage_id.hex}:{prompt_hash(prompt)[:32]}", prompt=prompt,
                prompt_hash=prompt_hash(prompt), status=AiImageStatus.COMPLETED,
                storage_key=storage_key_for(image_id), mime_type="image/png", size_bytes=1,
            )
        )
        await session.commit()

    async def cleanup():
        async with AsyncSessionLocal() as session:
            await session.execute(delete(WorldModel).where(WorldModel.id == world_id))
            await session.commit()
        async with AsyncSessionLocal() as session:
            repo = SqlUserRepository(session)
            await repo.delete(teacher.id)
            await repo.delete(student.id)

    return {"teacher": teacher, "student": student, "stage_id": stage_id, "image_id": image_id}, cleanup


async def _login(client: httpx.AsyncClient, email: str) -> str:
    response = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    response.raise_for_status()
    return response.json()["token"]


def _scenarios(data: dict, teacher_token: str, student_token: str) -> dict:
    t = {"headers": {"Authorization": f"Bearer {teacher_token}"}}
    s = {"headers": {"Authorization": f"Bearer {student_token}"}}
    return {
        "GET /health/live (sem banco)": lambda i: ("GET", "/health/live", {}, {200}),
        "GET /health/ready (SELECT 1)": lambda i: ("GET", "/health/ready", {}, {200}),
        "GET /api/users/{id} (auth + 2 queries)": lambda i: ("GET", f"/api/users/{data['student'].id}", s, {200}),
        "GET /api/users/ (lista todos)": lambda i: ("GET", "/api/users/", t, {200}),
        "POST /api/stages/{id}/illustration (cache)": lambda i: ("POST", f"/api/stages/{data['stage_id']}/illustration", s, {200}),
        "GET /api/ai-images/{id}": lambda i: ("GET", f"/api/ai-images/{data['image_id']}", s, {200}),
        "POST /api/auth/login (PBKDF2)": lambda i: (
            "POST", "/api/auth/login", {"json": {"email": data["student"].email, "password": PASSWORD}}, {200},
        ),
    }


async def _mysql_top_queries(admin_url: str, schema: str, limit: int = 10) -> list[dict]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(admin_url)
    query = text(
        """
        SELECT DIGEST_TEXT, COUNT_STAR, ROUND(AVG_TIMER_WAIT / 1e9, 3) AS avg_ms,
               ROUND(MAX_TIMER_WAIT / 1e9, 3) AS max_ms, SUM_ROWS_EXAMINED, SUM_ROWS_SENT,
               SUM_NO_INDEX_USED, SUM_CREATED_TMP_DISK_TABLES
        FROM performance_schema.events_statements_summary_by_digest
        WHERE SCHEMA_NAME = :schema AND DIGEST_TEXT NOT LIKE 'SHOW%' AND DIGEST_TEXT NOT LIKE 'SET%'
        ORDER BY SUM_TIMER_WAIT DESC LIMIT :limit
        """
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(query, {"schema": schema, "limit": limit})).mappings().all()
    await engine.dispose()
    return [dict(r) for r in rows]


async def _reset_digests(admin_url: str) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(admin_url)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE performance_schema.events_statements_summary_by_digest"))
    await engine.dispose()


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--concorrencia", type=int, nargs="+", default=[1, 10, 50])
    parser.add_argument("--requisicoes", type=int, default=300, help="por cenário e nível de concorrência")
    parser.add_argument("--aquecimento", type=int, default=20)
    parser.add_argument("--cenarios", nargs="*", default=None, help="trechos do nome dos cenários a rodar")
    parser.add_argument("--pid", type=int, default=None, help="pid do processo da API (CPU/RSS)")
    parser.add_argument("--mysql-admin-url", default=None, help="mysql+aiomysql://root:...@host:3306 (performance_schema)")
    parser.add_argument("--json", default=None, help="grava os resultados neste arquivo")
    parser.add_argument("--sem-misto", action="store_true", help="pula o cenário misto (rota leve durante logins)")
    args = parser.parse_args(argv)

    data, cleanup = await _seed()
    sampler = ProcSampler(args.pid)
    results: list[Result] = []
    try:
        limits = httpx.Limits(max_connections=max(args.concorrencia) + 10, max_keepalive_connections=max(args.concorrencia) + 10)
        async with httpx.AsyncClient(base_url=args.url, limits=limits, timeout=60) as client:
            teacher_token = await _login(client, data["teacher"].email)
            student_token = await _login(client, data["student"].email)
            scenarios = _scenarios(data, teacher_token, student_token)
            if args.cenarios:
                scenarios = {k: v for k, v in scenarios.items() if any(c in k for c in args.cenarios)}
            if args.mysql_admin_url:
                await _reset_digests(args.mysql_admin_url)

            for name, build in scenarios.items():
                await _run(client, build, args.aquecimento, min(5, max(args.concorrencia)))
                for concurrency in args.concorrencia:
                    total = args.requisicoes if "login" not in name else max(concurrency * 4, args.requisicoes // 5)
                    started = sampler.start()
                    latencies, errors, elapsed = await _run(client, build, total, concurrency)
                    cpu, rss = sampler.stop(started)
                    latencies.sort()
                    result = Result(
                        scenario=name, concurrency=concurrency, requests=total, errors=errors,
                        rps=round(total / elapsed, 1),
                        p50_ms=round(_percentile(latencies, 0.50), 1),
                        p95_ms=round(_percentile(latencies, 0.95), 1),
                        p99_ms=round(_percentile(latencies, 0.99), 1),
                        max_ms=round(latencies[-1], 1),
                        cpu_percent=cpu, rss_mb=rss,
                    )
                    results.append(result)
                    print(
                        f"{name:48s} c={concurrency:<3d} rps={result.rps:<8} p50={result.p50_ms:<7} "
                        f"p95={result.p95_ms:<7} p99={result.p99_ms:<7} erros={errors}"
                        + (f" cpu={cpu}% rss={rss}MB" if cpu is not None else ""),
                        flush=True,
                    )
            if not args.sem_misto:
                # rota leve medida DURANTE logins: mostra se o hash de senha trava o event loop
                build_light = _scenarios(data, teacher_token, student_token)["GET /api/users/{id} (auth + 2 queries)"]
                build_login = _scenarios(data, teacher_token, student_token)["POST /api/auth/login (PBKDF2)"]
                login_task = asyncio.create_task(_run(client, build_login, 80, 10))
                await asyncio.sleep(0.2)
                latencies, errors, elapsed = await _run(client, build_light, 100, 1)
                await login_task
                latencies.sort()
                result = Result(
                    scenario="GET /api/users/{id} durante 10 logins simultâneos", concurrency=1,
                    requests=100, errors=errors, rps=round(100 / elapsed, 1),
                    p50_ms=round(_percentile(latencies, 0.50), 1), p95_ms=round(_percentile(latencies, 0.95), 1),
                    p99_ms=round(_percentile(latencies, 0.99), 1), max_ms=round(latencies[-1], 1),
                )
                results.append(result)
                print(f"{result.scenario:48s} c=1   rps={result.rps:<8} p50={result.p50_ms:<7} "
                      f"p95={result.p95_ms:<7} p99={result.p99_ms:<7} erros={errors}", flush=True)
        top = []
        if args.mysql_admin_url:
            top = await _mysql_top_queries(args.mysql_admin_url, os.getenv("DB_NAME", "ApoiaMaisDB"))
            print("\nConsultas mais caras (performance_schema):")
            for row in top:
                print(f"- {row['COUNT_STAR']:>6}x avg={row['avg_ms']}ms max={row['max_ms']}ms "
                      f"sem_indice={row['SUM_NO_INDEX_USED']} linhas_lidas={row['SUM_ROWS_EXAMINED']} :: {row['DIGEST_TEXT'][:110]}")
    finally:
        await cleanup()
        from app.infrastructure.database.session import engine

        await engine.dispose()

    if args.json:
        with open(args.json, "w") as f:
            json.dump({"results": [asdict(r) for r in results], "top_queries": top}, f, ensure_ascii=False, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
