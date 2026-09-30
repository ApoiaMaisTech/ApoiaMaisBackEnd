# app/core/

Configuração da aplicação, carregada de variáveis de ambiente com **Pydantic Settings**.

## Arquivo `config.py`

Define a classe `Settings` e a instância global `settings`. Os valores vêm das variáveis de ambiente do processo e, em seguida, do arquivo `.env` no diretório de execução.

| Variável             | Tipo | Padrão      | Obrigatória |
|----------------------|------|-------------|-------------|
| `DB_HOST`            | str  | `localhost` | Não |
| `DB_PORT`            | int  | `3306`      | Não |
| `DB_USER`            | str  | —           | Sim |
| `DB_PASSWORD`        | str  | `""`        | Não |
| `DB_NAME`            | str  | —           | Sim |
| `JWT_SECRET_KEY`     | str  | —           | Sim |
| `JWT_ALGORITHM`      | str  | `HS256`     | Não |
| `JWT_EXPIRE_MINUTES` | int  | `30`        | Não |

A propriedade `settings.DATABASE_URL` monta a URL `mysql+aiomysql://usuario:senha@host:porta/banco`.

Como `settings = Settings()` é executado na importação, a ausência de uma variável obrigatória faz a aplicação falhar ao iniciar.

## Quem usa `settings`

| Consumidor | Uso |
|------------|-----|
| `app/api/dependencies/services.py` | `JWT_SECRET_KEY` e `JWT_ALGORITHM` para gerar o token no login |
| `app/alembic/env.py` | `DATABASE_URL` para as migrations |

Alguns módulos ainda leem variáveis diretamente com `os.getenv`, sem passar por `settings`:

| Módulo | Variáveis | Observação |
|--------|-----------|------------|
| `app/infrastructure/database/session.py` | `DATABASE_URL` ou `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Chama `load_dotenv()` e usa padrões próprios (`root`, `ApoiaMaisDB`) |
| `app/infrastructure/security/jwt.py` | `JWT_SECRET_KEY` | Usado quando `JwtServiceImpl` é criado sem argumentos, caso da validação do token em `api/dependencies/auth.py` |

A consolidação de toda a leitura de configuração em `Settings` é uma melhoria pendente.

## Arquivo `.env`

Use [`../../.env.example`](../../.env.example) como base. O `.env` é ignorado pelo Git.

O `.env.example` também lista `REDIS_URL` e `RABBITMQ_URL`, que ainda não são lidas pelo código. O `docker-compose.yml` usa, além das variáveis acima, `RABBITMQ_DEFAULT_USER` e `RABBITMQ_DEFAULT_PASS` para configurar o container do RabbitMQ.

## Uso

```python
from app.core.config import settings

settings.DATABASE_URL
settings.JWT_EXPIRE_MINUTES
```

## Boas práticas

- Nunca versione o `.env` nem coloque valores reais no `.env.example`.
- Em produção, injete os valores por variável de ambiente a partir de um gerenciador de segredos.
- `JWT_SECRET_KEY` deve ser um valor longo e aleatório, diferente em cada ambiente.
