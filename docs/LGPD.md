# LGPD no backend ApoiaMais

O ApoiaMais atende **crianças em tratamento de saúde**. Isso põe o projeto nos dois
casos mais exigentes da LGPD (Lei 13.709/2018): dados de crianças (art. 14) e dados
de saúde, que são **dados pessoais sensíveis** (art. 5º, II, e art. 11). Este documento
diz o que guardamos, por quê, por quanto tempo e quais controles existem no código.

> Não é parecer jurídico. As bases legais e prazos abaixo precisam ser validados pelo
> encarregado (DPO) da instituição que operar a plataforma.

## 1. Inventário de dados pessoais

| Tabela | Dados pessoais | Categoria | Titular |
|---|---|---|---|
| `user` | `name`, `email`, `password_hash` (PBKDF2, nunca a senha) | comum | aluno, professor, admin, médico |
| `patient` | `name`, `birth_date`, `interest`, `current_happiness`, `url_avatar` | **criança**; humor é dado de bem-estar | criança |
| `patient_clinical` | `clinical_rate` | **sensível (saúde)** | criança |
| `patient_progress`, `patient_achievement`, `patient_inventory` | desempenho e itens no jogo | criança | criança |
| `ai_content` | `generated_text`, `prompt`, `media_url` ligados ao paciente | criança | criança |
| `guardian` | `name`, `parentage`, `phone`, `email` | comum | responsável legal |
| `notification` | `title`, `message`, `receiver_id` | comum | destinatário |
| `files` | `original_name`, `url`, `owner_id` | depende do arquivo | dono |
| `login_acao` (auditoria) | `user_id`, `ip`, `user_agent`, `old_data`/`new_data` | registro de acesso | usuário |
| `log_error` | `user_id`, `message`, `stack_trace` | técnico (pode conter dado pessoal) | usuário |
| `ai_image` | `requested_by_user_id` (o prompt **não** tem dado da criança) | pseudonimizado | usuário |
| `outbox_event`, `processed_event` | ids de eventos e de imagens | técnico | — |

Fora do MySQL:

| Onde | O quê |
|---|---|
| Logs da API e dos workers | só ids (pseudônimos), rota, status, duração e `correlation_id`; ver seção 4 |
| RabbitMQ | envelopes de evento; hoje só `ai.image.*` (sem dado da criança) |
| Redis | contadores de rate limit por `user_id`/IP; travas do go-worker |
| Storage de mídia | ilustrações por fase (iguais para todas as crianças; não são dado pessoal) |
| Token JWT (no navegador) | `user_id`, `role`, `iat`, `exp` — sem e-mail nem nome |

## 2. Finalidade e base legal (proposta)

| Tratamento | Finalidade | Base legal |
|---|---|---|
| Conta de profissionais (`user`) | autenticação e autorização | execução de contrato / legítimo interesse (art. 7º, V e IX) |
| Dados da criança no jogo | atividade pedagógica e lúdica durante o tratamento | **melhor interesse da criança** e consentimento específico de um dos pais/responsável (art. 14, §1º) |
| Dado clínico | adaptar a atividade à condição de saúde | tutela da saúde, por profissionais de saúde (art. 11, II, "f") ou consentimento específico e destacado (art. 11, I) |
| Auditoria de acesso | segurança e obrigação legal | cumprimento de obrigação legal (Marco Civil, art. 15; LGPD art. 7º, II) |
| Logs técnicos | operação e diagnóstico | legítimo interesse, com minimização (art. 7º, IX; art. 10) |

## 3. Retenção

Aplicada pelo `api-worker` a cada `RETENTION_INTERVAL_HOURS` (padrão 24 h) e sob demanda com
`python -m scripts.aplicar_retencao`. Código: `app/infrastructure/database/retention.py`.

| Dado | Prazo padrão | Variável |
|---|---|---|
| Eventos consumidos (`processed_event`) | 30 dias | `RETENTION_PROCESSED_EVENT_DAYS` |
| Eventos publicados (`outbox_event`) | 7 dias (pendentes nunca saem) | `RETENTION_OUTBOX_PUBLISHED_DAYS` |
| Logs de erro (`log_error`) | 90 dias | `RETENTION_ERROR_LOG_DAYS` |
| Notificações lidas | 180 dias (não lidas ficam) | `RETENTION_READ_NOTIFICATION_DAYS` |
| Auditoria (`login_acao`) | 180 dias, **mínimo obrigatório** | `RETENTION_AUDIT_LOG_DAYS` |
| Conta, paciente, dado clínico, progresso | enquanto houver vínculo com a instituição; saem na exclusão | — |
| Logs de container (stdout) | definido na plataforma de logs; recomendado ≤ 30 dias | — |

A política recusa prazos de auditoria abaixo de 180 dias (Marco Civil, art. 15).

## 4. Controles no código

| Controle | Onde | Teste |
|---|---|---|
| Logs sem dado pessoal: campos sensíveis (senha, token, e-mail, CPF, telefone, nascimento, clínico...) viram `[redacted]`; e-mails, JWTs, `Bearer`, CPFs e hashes em texto livre e **tracebacks** viram marcadores | `app/core/redaction.py`, pipeline em `app/core/logging.py` | `tests/unit/test_redaction.py` |
| Mensagens de erro do SQLAlchemy sem os valores (`hide_parameters=True`) e sem o bloco `[parameters: ...]` | `app/infrastructure/database/session.py` | `tests/integration/api/test_lgpd.py` |
| Texto de erro gravado fora do processo (header `x-last-error` no RabbitMQ, `outbox_event.last_error`) passa pela mesma limpeza | `consumer.py`, `outbox.py` | `test_redaction.py` |
| Log de acesso sem query string nem corpo; uvicorn com `--no-access-log` | `app/api/middleware/correlation.py`, `Dockerfile` | `test_lgpd.py` |
| `SQL_ECHO` desligado por padrão (SQL com dados não vai para o log) | `session.py` | — |
| JWT só com `user_id` e `role` (payload é legível em base64) | `app/infrastructure/security/jwt.py` | `test_lgpd.py` |
| Respostas de erro não ecoam valores enviados (senha) nem detalhes internos | `app/api/exception_handlers.py` | `test_error_handling.py` |
| Login não revela se o e-mail existe | `login_usecase.py` | `test_users.py` |
| Conta removida perde o acesso na hora; perfil vale o do banco | `app/api/dependencies/auth.py` | `test_authorization_matrix.py` |
| Acesso a contas de outros usuários negado por padrão (admin e médico também) | rotas + matriz | `test_authorization_matrix.py` |
| Prompt de IA montado só no servidor, sem dado da criança; o go-worker não acessa o MySQL | `illustration_prompt.py`, `docs/ARQUITETURA.md` | `test_illustration_prompt.py` |
| Exclusão em cascata: apagar o paciente apaga dado clínico, progresso, conquistas, inventário e conteúdo de IA | FKs `ON DELETE CASCADE` | `test_schema_integrity.py` |
| Nenhuma FK sem regra de exclusão (exclusão não emperra) | schema | `test_schema_integrity.py` |
| Retenção automática com prazos mínimos legais | `retention.py`, `app/worker.py` | `tests/integration/database/test_retention.py` |
| Documentação da API fechada por padrão (`ENABLE_DOCS=false`) | `main.py` | `test_exposure_and_observability.py` |

## 5. Direitos do titular (art. 18)

| Direito | Como atender hoje | Situação |
|---|---|---|
| Confirmação e acesso | `GET /api/users/{id}` (a própria conta) | parcial: não há exportação dos dados da criança (não há rotas de paciente ainda) |
| Correção | `PUT /api/users/{id}` (e-mail e senha) | parcial |
| Eliminação | `DELETE /api/users/{id}` (professor remove aluno); exclusão do paciente apaga os dados ligados em cascata | parcial: não há rota de paciente; trilha de auditoria fica pelo prazo legal |
| Portabilidade | — | pendente |
| Revogação do consentimento | — | pendente (exige registro de consentimento) |

## 6. Crianças e dados de saúde: salvaguardas adicionais

Já existem:

- nenhum dado da criança vai ao provedor de IA nem ao go-worker; ilustrações são por fase;
- dado clínico isolado em `patient_clinical` (1:1 com o paciente) e apagado com ele;
- toda rota exige autenticação e a matriz de autorização nega por padrão.

Pendências antes de guardar dados reais de pacientes (precisam de decisão de produto/DPO):

1. **Rotas de paciente com autorização por vínculo** (profissional responsável pela criança),
   cobertas pela matriz de autorização. Hoje não há vínculo entre `user` e `patient`.
2. **Criptografia em nível de aplicação de `patient_clinical.clinical_rate`** (chave fora do
   banco, rotação), além da criptografia em repouso do MySQL e do volume/bucket.
3. **Registro de consentimento** do responsável (quem, quando, para quê, versão do termo) e
   fluxo de revogação.
4. **Auditoria de leitura** de dado clínico em `login_acao` (quem viu o quê). Ao gravar
   `old_data`/`new_data`, passar por `app.core.redaction.redact` (sem senha/hash).
5. **Exportação** dos dados do titular (art. 18, II e V) em formato estruturado.
6. **RIPD** (relatório de impacto, art. 38) e registro das operações (art. 37).
7. Backups com o mesmo prazo de retenção e criptografados.

## 7. Regras para quem desenvolve

- Nunca logar corpo de requisição, query string, token, senha ou objeto de usuário/paciente.
  Logue ids e use `extra={...}` com nomes claros — a limpeza é rede de segurança, não licença.
- Campo novo com dado pessoal: adicione na tabela da seção 1; se for sensível, verifique se o
  nome está coberto por `SENSITIVE_KEY_PARTS` em `app/core/redaction.py`.
- Tabela nova com dado pessoal: defina prazo (seção 3) e `ON DELETE` para o titular.
- Payload de evento nunca carrega dado da criança; use ids e deixe o consumidor buscar o que
  precisa (só a API acessa o MySQL).
- Texto de exceção que sai do processo (header, coluna, resposta): use `safe_error_text(exc)`.
