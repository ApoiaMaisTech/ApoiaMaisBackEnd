# rust-evaluator

Worker em Rust que **corrige atividades** do ApoiaMais de forma determinística.
Recebe `evaluation.requested` pelo RabbitMQ e devolve `evaluation.completed` ou
`evaluation.failed`. Não acessa o MySQL: a API (FastAPI) continua dona dos dados,
da autenticação e das regras de negócio; este serviço só avalia.

```
api (FastAPI) --outbox--> api-worker --> [apoiamais.events] --evaluation.requested--> rust-evaluator
                                                     ^                                      |
api-worker (inbox, log) <--evaluation.completed/failed----------------------------------------+
```

## Responsabilidades

- consumir `evaluation.requested` v1 da fila `rust-evaluator.evaluation`;
- validar envelope e payload contra o contrato (campos desconhecidos são recusados);
- corrigir cada item com regras determinísticas (abaixo);
- publicar o resultado em `apoiamais.events` com **publisher confirms**;
- tratar mensagem inválida e falha de publicação sem perder nada (retry, DLQ);
- logs JSON com `correlation_id` e `event_id`, e `/healthz` + `/readyz`.

Fora do escopo (decisão da issue #26): executar código enviado por usuário,
banco próprio, endpoints HTTP de negócio.

## Contratos

Em [`contracts/events`](../../contracts/events) (mesmo envelope de todos os eventos):

| Evento | Direção | Schema |
|---|---|---|
| `evaluation.requested` v1 | API → rust-evaluator | `evaluation.requested.v1.schema.json` |
| `evaluation.completed` v1 | rust-evaluator → API | `evaluation.completed.v1.schema.json` |
| `evaluation.failed` v1 | rust-evaluator → API | `evaluation.failed.v1.schema.json` |

O exemplo `evaluation.completed.v1.json` é **a saída exata** do exemplo
`evaluation.requested.v1.json`: o teste `tests/contracts.rs` confere isso, e o
Python valida o mesmo exemplo contra o JSON Schema. Assim Rust e Python concordam
sobre formato **e** regras sem compartilhar código.

LGPD: o pedido leva só gabarito e respostas. Nada que identifique a criança entra no
evento, e as respostas nunca vão para o log.

## Regras de correção

| `kind` | `answer` | Correto quando | Nota (0..1) |
|---|---|---|---|
| `text` | 1 valor | distância de edição ≤ erros permitidos contra algum `expected` | `1 - distância / tamanho do gabarito` |
| `choice` | 0..50 opções marcadas | conjunto marcado = conjunto `expected` | Jaccard: acertos / união |
| `number` | 1 valor | `|resposta - gabarito| ≤ tolerance` para algum `expected` | 1 ou 0 |

- Texto: espaços nas pontas removidos e internos colapsados, Unicode NFC.
  `ignore_case` (padrão `true`) e `ignore_accents` (padrão `false`: "avó" ≠ "avô").
- Erros permitidos = `min(max_typos, tamanho do gabarito / 4)`: palavras com menos de 4
  letras não ganham tolerância (com 1 erro em "a", qualquer letra passaria).
- Número: aceita `3`, `-2`, `3.5` e `3,5`. Resposta que não é número ("três") é resposta
  errada; **gabarito** que não é número é pedido inválido.
- Nota geral = média das notas dos itens (4 casas decimais).

## O que acontece com cada mensagem

| Situação | Resultado |
|---|---|
| Pedido válido | publica `evaluation.completed`; ack |
| Payload fora do contrato, com `evaluation_id` válido | publica `evaluation.failed` (`invalid_request`, `retryable: false`); ack |
| Envelope inválido, sem `evaluation_id`, evento/versão desconhecidos, maior que `MAX_MESSAGE_BYTES` | DLQ (`rust-evaluator.evaluation.dlq`) com `x-last-error`; ack |
| Falha ao publicar o resultado (broker) | retry em `….retry.10000/60000/300000` com `x-retry-count`; depois de `MAX_RETRIES`, DLQ |
| Falha ao republicar | nack com requeue (`x-delivery-limit=10` da fila quorum impede loop) |
| Reentrega do mesmo pedido | mesmo resultado com o **mesmo `event_id`** (UUID v5 do pedido): o inbox da API descarta a duplicata |
| SIGTERM | para de receber, termina o que está em andamento (até `DRAIN_TIMEOUT_SECONDS`) e fecha |
| RabbitMQ cai | reconecta sozinho com backoff de 1 s a 30 s; `/readyz` responde 503 enquanto isso |

A topologia (exchanges, filas de retry, DLQ e argumentos) é idêntica à do Python e do
Go (`src/topology.rs`). Para reprocessar a DLQ depois de corrigir a causa:
`python -m scripts.reprocessar_dlq --fila rust-evaluator.evaluation`.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `AMQP_URL` | obrigatória | `amqp://usuario:senha@rabbitmq:5672/` (sem vhost = `/`, como no Python e no Go) |
| `EVALUATOR_QUEUE` | `rust-evaluator.evaluation` | fila consumida (DLQ = `<fila>.dlq`) |
| `PREFETCH` | `16` | mensagens em processamento ao mesmo tempo |
| `MAX_RETRIES` | `3` | tentativas de publicar o resultado antes da DLQ |
| `MAX_MESSAGE_BYTES` | `262144` | mensagens maiores vão para a DLQ |
| `DRAIN_TIMEOUT_SECONDS` | `15` | espera pelas mensagens em andamento ao encerrar |
| `HEALTH_ADDR` | `0.0.0.0:8082` | `/healthz` e `/readyz` (só na rede interna) |
| `LOG_LEVEL` | `info,lapin=warn` | filtro do `tracing` |

No `docker-compose.yml`: `EVALUATOR_PREFETCH`, `EVALUATOR_MAX_RETRIES` e
`EVALUATOR_LOG_LEVEL` no `.env`.

## Rodar e testar

```bash
cd workers/rust-evaluator
cargo test                                   # unitários + contrato
AMQP_TEST_URL=amqp://test:test@127.0.0.1:5672/%2f cargo test   # + RabbitMQ real
cargo fmt --check && cargo clippy --all-targets -- -D warnings
AMQP_URL=amqp://guest:guest@127.0.0.1:5672/ cargo run --release
```

Fluxo completo no compose:

```bash
docker compose up --build -d
docker compose run --rm api-worker python -m scripts.publicar_avaliacao_exemplo
docker compose logs -f api-worker rust-evaluator   # "avaliação concluída", mesmo correlation_id
```

## Estrutura

```text
src/
├── main.rs        sinais, logs JSON, health server, laço do consumidor
├── config.rs      variáveis de ambiente
├── topology.rs    nomes e argumentos do RabbitMQ (iguais aos do Python e do Go)
├── broker.rs      declaração, consumo, publish com confirm, retry/DLQ, reconexão, drain
├── handler.rs     decide o destino de cada mensagem (sem I/O)
├── events.rs      envelope, payloads v1 e validação do contrato
├── evaluate.rs    regras de correção (puras e determinísticas)
└── health.rs      /healthz, /readyz e o subcomando `healthcheck` do Docker
tests/
├── contracts.rs   exemplos de contracts/events (os mesmos do Python e do Go)
└── rabbitmq.rs    fluxo real: completed, failed, DLQ e reentrega (AMQP_TEST_URL)
```

## Evoluções previstas

- Avaliação de áudio/pronúncia (`AIContentType.AUDIO`) e outras regras: novo `kind`
  com campo opcional (mesma versão) ou `evaluation.requested` v2.
- Execução isolada de código enviado pelo usuário exige desenho de segurança próprio
  (sandbox/WASM) antes de qualquer implementação.
- Persistir o resultado: quando a atividade tiver tabela na API, o handler
  `app/infrastructure/messaging/handlers/evaluation_results.py` grava na mesma
  transação da marca de processado.
