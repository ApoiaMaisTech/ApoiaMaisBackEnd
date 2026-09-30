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
- A migration inicial foi ajustada manualmente e difere dos models em alguns pontos (tipos de data, `ondelete` de `patient_clinical`, tamanho de `message` e `stack_trace` em `log_error`). Revise o resultado de qualquer `--autogenerate`.

## Scripts SQL legados (`models/auth-db/`)

`schema.sql`, `indexes.sql` e `seeds.sql` descrevem uma tabela `Usuario` com colunas em português, anterior ao Alembic. Não são executados pelo `docker-compose.yml` nem pelas migrations. O schema oficial é o gerado pelo Alembic.

## Como adicionar uma tabela

1. Criar o model em `models/<dominio>/`, herdando `Base` e, quando fizer sentido, `TimestampMixin`.
2. Importar o model em `models/__init__.py` e em `app/alembic/env.py`, para que o autogenerate o encontre.
3. Gerar e revisar a migration (veja [`../../alembic/README`](../../alembic/README)).
4. Criar a interface do repositório em `app/domain/repositories/` e a implementação em `repositories/`.
