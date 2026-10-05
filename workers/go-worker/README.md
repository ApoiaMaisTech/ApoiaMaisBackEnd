# go-worker

Worker em Go que gera as ilustrações das fases do jogo. Consome `ai.image.requested`
do RabbitMQ, chama o provedor de IA, grava o PNG no storage e publica
`ai.image.started`, `ai.image.generated` ou `ai.image.failed`.

**Não acessa o MySQL** (não tem credenciais). Arquitetura completa em
[`docs/ARQUITETURA.md`](../../docs/ARQUITETURA.md).

## Estrutura

```text
cmd/worker/          main: configuração, health server, sinal de término
internal/broker/     topologia (espelho de app/infrastructure/messaging/topology.py),
                     consumo com ack manual, retry, DLQ, reconexão e publisher confirms
internal/events/     envelope e payloads v1 (contrato em contracts/events)
internal/imagejob/   fluxo do job: idempotência, moderação, orçamento, provedor, storage
internal/provider/   fake (padrão, sem custo) e OpenAI (POST /v1/images/generations)
internal/moderation/ bloqueio de temas impróprios antes de gastar com o provedor
internal/guard/      Redis: concluído, trava por job, orçamento diário
internal/storage/    volume local ou S3/compatível
```

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `AMQP_URL` | — | obrigatório |
| `REDIS_URL` | — | obrigatório |
| `AI_PROVIDER` | `fake` | `fake` ou `openai` |
| `OPENAI_API_KEY` | — | obrigatório com `openai` |
| `AI_IMAGE_MODEL` | `gpt-image-1` | modelo do provedor |
| `AI_DAILY_IMAGE_BUDGET` | `200` | gerações por dia (UTC), todas as réplicas |
| `AI_REQUEST_TIMEOUT_SECONDS` | `120` | timeout da chamada ao provedor |
| `WORKER_CONCURRENCY` | `4` | jobs em paralelo (= prefetch) |
| `MAX_RETRIES` | `3` | tentativas antes da DLQ |
| `STORAGE_BACKEND` | `local` | `local` ou `s3` |
| `STORAGE_LOCAL_DIR` | `/data/media` | |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_USE_SSL` | | com `s3` |
| `HEALTH_ADDR` | `:8081` | `/healthz` e `/readyz`, só rede interna |

## Desenvolvimento

```bash
cd workers/go-worker
go test ./...                                   # unitários
AMQP_TEST_URL=amqp://test:test@localhost:5672/ go test -race ./...   # + RabbitMQ real
S3_TEST_ENDPOINT=localhost:8333 S3_TEST_BUCKET=apoiamais-test \
  S3_TEST_ACCESS_KEY=... S3_TEST_SECRET_KEY=... go test ./internal/storage/
```

A imagem final é `scratch` (sem shell), roda como UID 10001 e tem ~15 MB.
