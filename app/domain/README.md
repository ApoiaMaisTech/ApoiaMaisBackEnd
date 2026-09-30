# app/domain/

Camada de domínio. Contém as entidades, os enums, as exceções de negócio e as **interfaces** (classes abstratas) que a infraestrutura implementa. Não importa FastAPI, SQLAlchemy nem nenhuma outra camada do projeto.

## Estrutura

```text
domain/
├── entities/
│   └── user.py                  Entidade User (dataclass)
├── enums/
│   ├── user.py                  UserRole
│   ├── ai_content_type.py       AIContentType
│   ├── audit.py                 AuditAction, LogLevel
│   ├── file.py                  FileOwnerType, FileCategory
│   ├── gamification.py          ItemType
│   ├── happiness.py             Happiness
│   ├── notification.py          NotificationType
│   └── store_item.py            StoreItemType
├── exceptions/
│   ├── base.py                  DomainException
│   ├── email_already_exists.py  EmailAlreadyExistsException
│   ├── invalid_credentials.py   InvalidCredentialsException
│   └── user_not_found.py        UserNotFoundException
├── repositories/
│   └── user_repository.py       UserRepository (ABC)
└── services/
    ├── jwt_service.py           JwtService (ABC)
    └── password_service.py      PasswordService (ABC)
```

## Entidade `User`

```python
@dataclass
class User:
    id: UUID | None
    name: str
    email: str
    password_hash: str
    role: UserRole
```

É a única entidade de domínio até o momento. As demais tabelas (pacientes, gamificação etc.) existem só como models SQLAlchemy.

## Enums

| Enum               | Valores |
|--------------------|---------|
| `UserRole`         | `student`, `teacher`, `administrador`, `medico` |
| `AIContentType`    | `story`, `image`, `exercise`, `audio` |
| `AuditAction`      | `criar`, `atualizar`, `deletar`, `login`, `logout`, `visualizar` |
| `LogLevel`         | `info`, `warning`, `error`, `critical` |
| `FileOwnerType`    | `paciente`, `usuario`, `item_loja`, `conquista` |
| `FileCategory`     | `avatar`, `midia_ia`, `imagem_item`, `icone_conquista`, `outro` |
| `ItemType`         | `avatar`, `fundo`, `acessorio` (não referenciado; duplica `StoreItemType`) |
| `StoreItemType`    | `avatar`, `fundo`, `acessorio` |
| `Happiness`        | `feliz`, `triste`, `neutra`, `irritado` |
| `NotificationType` | `conquista`, `progresso`, `sistema`, `lembrete` |

Observações sobre `UserRole`:

- A coluna `user.role` da migration atual aceita apenas `STUDENT` e `TEACHER`. As roles `ADMIN` e `DOCTOR` existem no enum, mas ainda não podem ser gravadas.
- O banco armazena o **nome** do membro (`STUDENT`), e a API e o token trafegam o **valor** (`student`).

## Exceções

Todas herdam de `DomainException`, que guarda a mensagem em `exc.message`.

| Exceção                       | Lançada por |
|-------------------------------|-------------|
| `UserNotFoundException`       | Login, busca, atualização e remoção de usuário |
| `EmailAlreadyExistsException` | Criação e atualização de usuário |
| `InvalidCredentialsException` | Login com senha incorreta |

O handler global (`app/api/exception_handlers.py`) converte qualquer `DomainException` em **400**. A rota de login captura `UserNotFoundException` e `InvalidCredentialsException` antes, respondendo 404 e 401. As exceções ainda não carregam código de status próprio.

## Interfaces

| Interface         | Métodos | Implementação |
|-------------------|---------|---------------|
| `UserRepository`  | `create`, `get_by_id`, `get_by_email`, `list`, `update`, `delete` (todos `async`) | `SqlUserRepository` |
| `PasswordService` | `hash(password)`, `verify(plain, hashed)` | `PasswordServiceImpl` |
| `JwtService`      | `generate_token(user_id, role)`, `verify_token(token)` | `JwtServiceImpl` |

Divergência conhecida: `JwtServiceImpl` não herda de `JwtService`, e seu `generate_token` recebe `(user_id, user_email, role)`. O `LoginUseCase` chama a assinatura da implementação.

## Regras da camada

- Sem dependência de frameworks ou bibliotecas de infraestrutura.
- Novas regras de negócio devem ser expressas por entidades e exceções deste pacote.
- Novos repositórios e serviços externos começam por uma interface aqui.
