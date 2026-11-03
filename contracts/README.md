# Contratos de eventos

JSON Schemas dos eventos trocados pelo RabbitMQ. São a fonte de verdade entre a API
(Python) e os workers (Go e Rust):

- `events/envelope.v1.schema.json`: envelope comum a todas as mensagens.
- `events/<event_type>.v<versão>.schema.json`: payload de cada evento.
- `events/examples/*.json`: um exemplo completo por evento. Os testes de contrato do
  Python (`tests/unit/test_event_contracts.py`), do Go
  (`workers/go-worker/internal/events/events_test.go`) e do Rust
  (`workers/rust-evaluator/tests/contracts.rs`) leem estes mesmos arquivos.
- `evaluation.completed.v1.json` é a saída exata do rust-evaluator para
  `evaluation.requested.v1.json` (o teste do Rust confere): mudar uma regra de correção
  exige atualizar o exemplo.

## Regras de versionamento

1. Campo novo **opcional**: mesma versão. Como os schemas usam
   `additionalProperties: false` (os consumidores recusam campos desconhecidos),
   atualize primeiro os consumidores para aceitar o campo e só depois os produtores.
2. Qualquer outra mudança (remover, renomear, tornar obrigatório, mudar tipo): crie
   `vN+1` com schema e exemplo novos. Os consumidores aceitam as duas versões até
   todos os produtores migrarem.
3. Todo evento novo precisa de schema + exemplo, ou o teste de contrato falha.
