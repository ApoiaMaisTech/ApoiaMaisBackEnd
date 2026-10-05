# app/infrastructure/

Camada de infraestrutura. Implementa as interfaces do domínio usando bibliotecas externas: **SQLAlchemy assíncrono** (MySQL via `aiomysql`) para persistência, **PyJWT** para tokens e `hashlib` (PBKDF2) para senhas.

## Estrutura

```text
infrastructure/
├── database/                  Persistência (veja database/README.md)
│   ├── base.py                DeclarativeBase
│   ├── mixins.py              TimestampMixin (created_at, updated_at)
│   ├── session.py             Engine assíncrono e AsyncSessionLocal
│   ├── mappers/               user_mapper.py (não utilizado)
│   ├── models/                Models SQLAlchemy por domínio
│   └── repositories/          SqlUserRepository
└── security/                  Segurança (veja security/README.md)
    ├── jwt.py                 JwtServiceImpl
    └── password.py            PasswordServiceImpl
```

Documentação detalhada:

- [`database/README.md`](database/README.md)
- [`security/README.md`](security/README.md)

## Implementações das interfaces do domínio

| Interface (domínio) | Implementação                                   |
|---------------------|-------------------------------------------------|
| `UserRepository`    | `database/repositories/sql_user_repository.py`  |
| `PasswordService`   | `security/password.py`                          |
| `JwtService`        | `security/jwt.py` (sem herança formal da interface) |

As implementações são instanciadas em `app/api/dependencies/`.

## Serviços externos

| Serviço  | Situação |
|----------|----------|
| MySQL 8.0 | Em uso, via SQLAlchemy assíncrono |
| Redis    | Rate limit (`rate_limit.py`); no go-worker, travas e orçamento de IA |
| RabbitMQ | `messaging/`: topologia, publisher com confirms, outbox, consumidor com retry/DLQ |
| Storage  | `storage/`: volume local ou S3/compatível (imagens geradas por IA) |

## Regras da camada

- Não contém regra de negócio: converte entre o mundo externo e as entidades do domínio.
- Não importa `app.api` nem `app.application`.
- Toda nova integração externa deve implementar uma interface definida em `app/domain/`.
