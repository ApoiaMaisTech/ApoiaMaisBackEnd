# Performance: linha de base, metas e achados

Medições da API (FastAPI + MySQL) para servir de referência: toda mudança que
mexa no caminho da requisição deve ser comparada com estes números.

## Como medir

```bash
# 1. API com rate limit desligado (senão ele vira o gargalo) e 1 processo, como no Dockerfile
RATE_LIMIT_ENABLED=false LOG_LEVEL=WARNING uvicorn main:app --port 8000 --no-access-log

# 2. em outro terminal (mesmas variáveis DB_* da API); --pid mede CPU e memória da API
python -m scripts.benchmark_api --pid <pid do uvicorn> --concorrencia 1 10 50 --requisicoes 300 \
  --mysql-admin-url mysql+aiomysql://root:<senha>@127.0.0.1:3306 --json resultado.json
```

O script cria um professor, um aluno, um mundo, uma fase e uma ilustração pronta, mede cada
cenário em cada nível de concorrência (com aquecimento), mede uma rota leve **durante** logins
simultâneos e, com `--mysql-admin-url`, lista as consultas mais caras do `performance_schema`.
Os dados são apagados no final.

### Ambiente da linha de base

| Item | Valor |
|---|---|
| Máquina | 4 vCPU, 16 GB (container Linux) |
| API | 1 processo uvicorn, Python 3.11, sem rate limit, logs em WARNING |
| Banco | MySQL 8.0 em Docker na mesma máquina, schema na head, ~60 usuários |
| Cliente | `scripts/benchmark_api.py` (httpx assíncrono) **na mesma máquina** |
| Data | 2026-11-03 |

Cliente, API e MySQL disputam os mesmos 4 núcleos: com concorrência 50 o próprio cliente
satura e os números variam bastante entre execuções. Compare sempre no mesmo ambiente e use
concorrência 1 e 10 como referência principal.

## Resultados

"Antes" é o código anterior a esta análise; "depois" inclui as duas correções da seção
[Achados](#achados) (hash de senha fora do event loop e pool de conexões). Latências em ms.

| Cenário | Conc. | req/s antes | req/s depois | p50 antes | p50 depois | p95 antes | p95 depois | p99 depois | CPU depois |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `GET /health/live` (sem banco) | 1 | 600 | 657 | 1.5 | 1.5 | 2.2 | 1.9 | 2.4 | 26% |
| `GET /health/live` | 10 | 667 | 650 | 9.1 | 8.3 | 24.4 | 31.0 | 333 | 17% |
| `GET /health/ready` (`SELECT 1`) | 1 | 131 | 162 | 7.6 | 6.0 | 9.4 | 7.3 | 7.8 | 36% |
| `GET /health/ready` | 10 | 378 | 359 | 19.4 | 18.8 | 66.3 | 82.5 | 125 | 47% |
| `GET /api/users/{id}` (auth + 2 consultas) | 1 | 67 | **96** | 14.5 | **10.3** | 18.6 | **13.3** | 15.3 | 52% |
| `GET /api/users/{id}` | 10 | 172 | **225** | 56.5 | **43.2** | 82.1 | **64.5** | 90.8 | 89% |
| `GET /api/users/{id}` | 50 | 138 | 127 | 311 | 271 | 825 | 1024 | 1398 | 63% |
| `GET /api/users/` (lista todos, ~60) | 1 | 40 | 42 | 24.8 | 24.3 | 31.2 | 30.5 | 32.6 | 72% |
| `GET /api/users/` | 10 | 70 | 65 | 142 | 143 | 194 | 225 | 259 | 97% |
| `POST /api/stages/{id}/illustration` (cache) | 1 | 57 | **68** | 17.9 | **14.6** | 21.2 | **18.9** | 23.3 | 45% |
| `POST /api/stages/{id}/illustration` | 10 | 150 | **170** | 64.3 | **57.5** | 94.6 | **81.1** | 101 | 94% |
| `GET /api/ai-images/{id}` | 1 | 65 | **77** | 15.2 | **12.9** | 18.6 | **16.0** | 19.0 | 44% |
| `GET /api/ai-images/{id}` | 10 | 173 | **198** | 57.5 | **44.1** | 73.5 | 93.2 | 197 | 84% |
| `POST /api/auth/login` (PBKDF2) | 1 | 11.0 | 11.6 | 81.6 | 76.7 | 125 | 121 | 139 | 92% |
| `POST /api/auth/login` | 10 | 12.8 | **43.6** | 709 | **221** | 1061 | **316** | 350 | **359%** |
| `POST /api/auth/login` | 50 | 13.3 | **51.4** | 3626 | **902** | 4663 | **1086** | 1129 | **370%** |
| `GET /api/users/{id}` **durante 10 logins** | 1 | 13.4 | **40.4** | 14.0 | 15.6 | **716** | **58.2** | 74.4 | — |

Memória (RSS) do processo da API: 89 MB parado, 94 MB no pico. Nenhum erro em nenhum cenário.

### Com 4 processos (`uvicorn --workers 4`, um por núcleo)

| Cenário | Conc. | req/s | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| `GET /api/users/{id}` | 10 | **401** | 22.0 | 44.6 | 54.1 |
| `POST /api/stages/{id}/illustration` | 10 | 248 | 32.9 | 93.9 | 203 |
| `POST /api/auth/login` | 10 | 42.4 | 224 | 358 | 419 |
| `GET /api/users/{id}` durante 10 logins | 1 | 46.6 | 17.8 | 40.8 | 50.5 |

### Consultas ao MySQL

Durante a bateria (performance_schema, por padrão de consulta):

| Consulta | Execuções | Média | Sem índice | Observação |
|---|---:|---:|---:|---|
| `user` por id (autenticação, a cada requisição) | 4.787 | 0,38 ms | 0 | chave primária |
| `ROLLBACK` (fim de sessão só de leitura) | 10.233 | 0,11 ms | 0 | normal no SQLAlchemy |
| `SELECT ... FROM user` (lista) | 918 | 0,41 ms | **919** | varredura completa, sem `LIMIT` |
| `ai_image` por `dedupe_key` / por id | 920 | 0,37 ms | 0 | índice único / PK |
| `stage JOIN world` (tema da fase) | 919 | 0,34 ms | 0 | PK |

Com volume (banco descartável: 50 mil usuários, 1.000 fases, 50 mil imagens, 20 mil eventos
no outbox, `ANALYZE TABLE` rodado), `EXPLAIN ANALYZE`:

| Consulta | Plano | Tempo |
|---|---|---:|
| login: `user` por email | índice único (`ix_user_email`) | < 0,1 ms |
| cache: `ai_image` por `dedupe_key` | índice único | < 0,1 ms |
| cota diária: `count(*)` por usuário desde 00h | range coberto por `ix_ai_image_requested_by` (1.193 linhas) | 1,9 ms |
| falha recente da fase | `ix_ai_image_stage_hash` | < 0,1 ms |
| relay do outbox (pendentes, 50 por vez) | range em `ix_outbox_event_pending` + sort de 200 linhas | 1,8 ms |
| **lista de usuários** | **table scan de 50 mil linhas** | 30,6 ms no banco |

E na API, com os mesmos 50 mil usuários:

| Requisição | Tempo | Resposta |
|---|---:|---:|
| `GET /api/users/{id}` | 11 ms | — |
| **`GET /api/users/`** | **6,7 a 7,4 s** | **5,7 MB** |

## Achados

### 1. Hash de senha travava o event loop (corrigido)

`PasswordServiceImpl` (PBKDF2-SHA256, 100 mil iterações, ~80 ms de CPU) era chamado direto
dentro dos use cases `async` de login, criação e atualização de usuário. Enquanto um hash
rodava, **nenhuma outra requisição do processo andava**: o login não passava de ~12 req/s com
qualquer concorrência, e uma rota leve tinha p95 de 716 ms durante 10 logins.

Correção: `await asyncio.to_thread(...)` nos três use cases. `hashlib.pbkdf2_hmac` libera o
GIL, então os hashes também passam a usar os outros núcleos (CPU de 92% para 360%).
Resultado: login 3,4x mais rápido em vazão (43,6 req/s), p95 de 1.061 para 316 ms a 10
simultâneos, e a rota leve durante logins de 716 para 58 ms de p95 (12x).
Teste de regressão: `tests/unit/test_password_off_event_loop.py`.

### 2. Uma conexão nova com o MySQL por requisição (corrigido)

O engine usava `NullPool`. Agora há pool por processo (`DB_POOL_SIZE=10`,
`DB_MAX_OVERFLOW=10`, `DB_POOL_RECYCLE_SECONDS=1800`; `DB_POOL_SIZE=0` volta ao comportamento
antigo). Ganho de 25% a 45% em vazão e 2 a 4 ms de p50 nas rotas que usam o banco.

Achado junto: `pool_pre_ping` quebra com SQLAlchemy 2.0.31 + aiomysql 0.2.0
(`TypeError` em `ping(reconnect)`), então não é usado; conexão derrubada é invalidada pelo
SQLAlchemy no primeiro erro de desconexão. Os testes rodam sem pool (o `TestClient` usa um
event loop por requisição), por isso `tests/integration/database/test_connection_pool.py`
exercita o engine com pool à parte.

### 3. `GET /api/users/` sem paginação (pendente, muda o contrato)

Lê e serializa **todos** os usuários (com validação de `EmailStr` em cada um na saída). Com
50 mil usuários leva ~7 s, devolve 5,7 MB e ocupa o processo inteiro nesse tempo: qualquer
professor consegue degradar a API para todos. Proposta (exige ajuste no frontend):

- `GET /api/users/?limit=50&offset=0` (máximo 200), ordenado por nome, com o total no header
  `X-Total-Count`;
- filtro por perfil (`?role=student`) para a tela do professor;
- `UserResponse.email` como `str` na saída (a validação já acontece na entrada).

### 4. A autenticação custa uma consulta por requisição (intencional)

Desde a issue #27, `get_current_user` confere o usuário no banco (conta removida perde o
acesso na hora). Custo medido: 0,38 ms no MySQL por requisição. Se um dia pesar, um cache
curto (ex.: 30 s no Redis) mantém quase todo o benefício.

### 5. Custo do PBKDF2

Cada login custa ~80 ms de CPU por núcleo: com 4 núcleos, o teto é ~50 logins/s por máquina.
É o preço da proteção contra força bruta e é adequado ao volume esperado (logins são raros
perto das outras requisições). A recomendação atual da OWASP para PBKDF2-SHA256 é 600 mil
iterações; subir para isso multiplica o custo por 6. Avaliar junto com uma migração para
Argon2id (re-hash no próximo login).

### 6. Um processo por container

O `Dockerfile` sobe 1 processo uvicorn. Com tudo em CPU, 1 processo satura um núcleo perto de
~200 req/s nas rotas autenticadas. Para escalar: `--workers N` (N = núcleos) ou mais réplicas
do container. Atenção ao total de conexões: `(DB_POOL_SIZE + DB_MAX_OVERFLOW) x processos`
deve ficar abaixo do `max_connections` do MySQL (151 por padrão).

## Metas (SLO propostos)

Cenário de referência: um hospital com até ~30 tablets jogando e alguns professores, ou seja,
concorrência de pico na casa de 10 a 30 requisições simultâneas por instância.

| Indicador | Meta por processo | Linha de base (depois) |
|---|---|---|
| Rotas autenticadas de leitura (`GET /api/users/{id}`, ilustração, imagem): p95 a 10 simultâneos | ≤ 100 ms | 64 a 93 ms ✔ |
| Vazão dessas rotas a 10 simultâneos | ≥ 150 req/s | 170 a 225 req/s ✔ |
| Login: p95 a 10 simultâneos | ≤ 500 ms | 316 ms ✔ |
| Rota leve durante logins simultâneos: p95 | ≤ 100 ms | 58 ms ✔ |
| `GET /health/live`: p95 a 10 simultâneos | ≤ 50 ms | 31 ms ✔ |
| Taxa de erro sob a carga acima | 0% | 0% ✔ |
| Consultas no caminho da requisição | todas por índice; ≤ 5 ms no banco | ✔ exceto a lista de usuários |
| `GET /api/users/` com 10 mil usuários | ≤ 300 ms | ✘ (~1,4 s estimado; 7 s com 50 mil) |
| Memória (RSS) por processo | ≤ 150 MB | 94 MB ✔ |

## Quando medir de novo

- mudança em dependência de autenticação, sessão de banco, middleware ou logging;
- rota nova que vá ser chamada pelo jogo em toda fase;
- troca de versão de FastAPI, SQLAlchemy, aiomysql ou Python;
- antes de mudar `DB_POOL_SIZE`, número de workers ou as iterações do PBKDF2.

Guarde o `--json` da execução junto do PR para comparar.
