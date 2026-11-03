# app/infrastructure/database/

Persistência com **SQLAlchemy 2.0 assíncrono** sobre **MySQL 8.0** (driver `aiomysql`). O schema é versionado pelo **Alembic** (veja [`../../alembic/README`](../../alembic/README)).

## Estrutura

```text
database/
├── __init__.py              Reexporta Base
├── base.py                  class Base(DeclarativeBase)
├── mixins.py                TimestampMixin
├── session.py               engine assíncrono e AsyncSessionLocal
├── mappers/
│   └── user_mapper.py       Não utilizado (a conversão está no repositório)
├── models/
│   ├── __init__.py          Importa todos os models
│   ├── auth/                UserModel
│   ├── audit/               AuditLogModel, AuditLogErrorModel
│   ├── file/                FileModel
│   ├── ludic/               World, Stage, Achievement, StoreItem, PatientProgress, PatientAchievement, AIContent
│   ├── notification/        NotificationModel
│   ├── patient/             Patient, Guardian, PatientClinical, PatientInventory
│   ├── messaging/           OutboxEvent, ProcessedEvent
│   └── auth-db/             Scripts SQL legados (não usados pelo Alembic)
└── repositories/
    └── sql_user_repository.py   SqlUserRepository
```

## Sessão (`session.py`)

```python
engine = create_async_engine(DATABASE_URL, echo=True, poolclass=NullPool)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
```

- A URL vem da variável `DATABASE_URL` ou é montada a partir de `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` e `DB_NAME` (lidas com `os.getenv`, não com `settings`).
- `NullPool`: cada requisição abre e fecha a própria conexão com o MySQL.
- `echo=True`: todo SQL executado é registrado no log.
- Uma sessão por requisição, criada em `app/api/dependencies/repositories.py`.

## Repositório `SqlUserRepository`

Implementa `UserRepository`. Converte `UserModel` em entidade `User` (e vice-versa) com os métodos estáticos `_to_entity` e `_to_model`.

| Método         | Implementação |
|----------------|---------------|
| `create`       | `add` + `commit` + `refresh` |
| `get_by_id`    | `session.get(UserModel, id)` |
| `get_by_email` | `select ... where email = :email` |
| `list`         | `select(UserModel)` sem paginação |
| `update`       | `merge` de um model novo + `commit` + `refresh` (redefine `is_active` como `True`) |
| `delete`       | `session.delete` + `commit` (sem erro se o id não existe) |

Cada método de escrita faz o próprio `commit`. Não há Unit of Work: operações com mais de um passo não ficam na mesma transação.

## Models e tabelas

Todos os models (exceto as tabelas associativas) herdam `TimestampMixin`, que adiciona `created_at` e `updated_at` com índice. As chaves primárias são UUID (`sa.Uuid`, armazenado como `CHAR(32)` no MySQL).

| Tabela                | Model                     | Relacionamentos (FK) |
|-----------------------|---------------------------|----------------------|
| `user`                | `UserModel`               | — |
| `patient`             | `PatientModel`            | `guardian_id` -> `guardian.id` (SET NULL) |
| `guardian`            | `GuardianModel`           | — |
| `patient_clinical`    | `PatientClinicalModel`    | `patient_id` -> `patient.id` (CASCADE na migration) |
| `patient_inventory`   | `PatientInventoryModel`   | `patient_id` -> `patient.id`, `item_id` -> `store_item.id` |
| `world`               | `WorldModel`              | — (`order` único) |
| `stage`               | `StageModel`              | `world_id` -> `world.id` |
| `patient_progress`    | `PatientProgressModel`    | `patient_id` -> `patient.id`, `stage_id` -> `stage.id` (único por paciente e fase) |
| `achievement`         | `AchievementModel`        | — |
| `patient_achievement` | `PatientAchievementModel` | `patient_id` -> `patient.id`, `achievement_id` -> `achievement.id` |
| `store_item`          | `StoreItemModel`          | — |
| `ai_content`          | `AIContentModel`          | `patient_id` -> `patient.id`, `stage_id` -> `stage.id` (SET NULL) |
| `files`               | `FileModel`               | Referência lógica `owner_id` + `owner_type`, sem FK |
| `notification`        | `NotificationModel`       | Referência lógica `receiver_id`, sem FK |
| `login_acao`          | `AuditLogModel`           | Referência lógica `user_id`, sem FK (log de auditoria) |
| `log_error`           | `AuditLogErrorModel`      | Referência lógica `user_id`, sem FK |

Apenas a tabela `user` é usada pelo código da aplicação. As demais não têm repositório nem caso de uso.

Pontos de atenção no modelo atual:

- Não existe vínculo entre `user` e `patient` (aluno ↔ paciente) nem entre professor e paciente.
- `patient.guardian_id` e `patient_clinical.patient_id` são `String(36)`, enquanto as chaves referenciadas são `Uuid` (`CHAR(32)`).
- Nenhum `relationship()` do SQLAlchemy está declarado.
- Models e migrations estão alinhados: `alembic check` não encontra diferenças, e o CI falha se
  surgir alguma (veja "Validação do schema" abaixo).

## Scripts SQL legados (`models/auth-db/`)

`schema.sql`, `indexes.sql` e `seeds.sql` descrevem uma tabela `Usuario` com colunas em português, anterior ao Alembic. Não são executados pelo `docker-compose.yml` nem pelas migrations. O schema oficial é o gerado pelo Alembic.

## Validação do schema

| O quê | Onde |
|---|---|
| Models x banco sem diferenças (`alembic check`) | CI (`ci.yml`) e `test_schema_integrity.py` |
| FK com o mesmo tipo da chave referenciada (`CHAR(32)` de `sa.Uuid`) | `test_schema_integrity.py` |
| Toda FK com `ON DELETE CASCADE` ou `SET NULL` explícito | `test_schema_integrity.py` |
| Unicidade (email, `dedupe_key`, progresso por fase, ordem do mundo) e chave do inbox | `test_schema_integrity.py` |
| Paciente → dado clínico em cascata; dado clínico sem paciente recusado | `test_schema_integrity.py` |
| Instalação do zero, `downgrade base` e reinstalação | `test_migrations.py` (banco descartável) |
| Escada: cada revisão sobe, desce e sobe de novo | `test_migrations.py` |
| Upgrade de um banco antigo **com dados** (preserva e normaliza) | `test_migrations.py` |
| `migrate` no Docker Compose com o `.env.example` | CI, job `docker` |

`test_migrations.py` cria bancos temporários e precisa de um usuário com permissão para isso:

```bash
MIGRATIONS_TEST_ADMIN_URL=mysql+pymysql://root:root@127.0.0.1:3306 pytest tests/integration/database
```

Cuidados ao escrever migrations para MySQL:

- `sa.Uuid` vira `CHAR(32)` (hex sem hífens). Coluna que aponta para um id deve ser `sa.Uuid`
  também, nunca `String(36)`: o valor com hífens não casa com a chave e a FK recusa o INSERT.
- No `downgrade`, use só `drop_table` (ele já remove os índices). Remover antes um índice que
  sustenta FK falha com o erro 1553.
- Índices compostos criados na migration precisam estar em `__table_args__` do model; senão o
  próximo `--autogenerate` propõe removê-los.

## Como adicionar uma tabela

1. Criar o model em `models/<dominio>/`, herdando `Base` e, quando fizer sentido, `TimestampMixin`.
2. Importar o model em `models/__init__.py` (o `app/alembic/env.py` importa esse pacote).
3. Gerar e revisar a migration (veja [`../../alembic/README`](../../alembic/README)); rode `alembic check`.
4. Criar a interface do repositório em `app/domain/repositories/` e a implementação em `repositories/`.
