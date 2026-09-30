# app/application/

Camada de aplicação. Contém os **casos de uso** (uma classe por ação de negócio) e os **DTOs** Pydantic que definem a entrada e a saída da API.

Os casos de uso dependem apenas das interfaces do domínio (`UserRepository`, `PasswordService`, `JwtService`). As implementações concretas são injetadas pela camada `api/`, o que permite testá-los com mocks, sem banco e sem FastAPI.

## Estrutura

```text
application/
├── common/
│   └── api_response.py            Modelo genérico de resposta (definido, ainda não usado)
├── dto/
│   ├── create_user_request.py     CreateUserRequest
│   ├── create_user_response.py    UserResponse
│   ├── login_request.py           LoginRequest
│   ├── token_response.py          TokenResponse e UserData
│   └── update_user_request.py     UpdateUserRequest
└── use_cases/
    ├── auth/
    │   └── login_usecase.py       LoginUseCase
    ├── users/                     CRUD de usuários
    └── reports/                   Não implementado
```

## DTOs

| DTO                 | Campos | Uso |
|---------------------|--------|-----|
| `CreateUserRequest` | `name` (3 a 100), `email` (EmailStr), `password` (mínimo 8) | Criar aluno ou professor |
| `UpdateUserRequest` | `email` (EmailStr), `password` | Atualizar usuário (os dois campos são obrigatórios) |
| `LoginRequest`      | `email` (EmailStr), `password` | Login |
| `UserResponse`      | `id`, `name`, `email`, `role` | Resposta das rotas de usuário |
| `TokenResponse`     | `token`, `user: UserData` | Resposta do login |

## Casos de uso

| Classe              | Arquivo                               | Dependências |
|---------------------|---------------------------------------|--------------|
| `LoginUseCase`      | `use_cases/auth/login_usecase.py`     | `UserRepository`, `PasswordService`, `JwtService` |
| `CreateUserUseCase` | `use_cases/users/create_user_usecase.py` | `UserRepository`, `PasswordService` |
| `GetUserUseCase`    | `use_cases/users/get_user_usecase.py` | `UserRepository` |
| `ListUserUseCase`   | `use_cases/users/list_user_usecase.py` | `UserRepository` |
| `UpdateUserUseCase` | `use_cases/users/update_user_usecase.py` | `UserRepository`, `PasswordService` |
| `DeleteUserUseCase` | `use_cases/users/delete_user_usecase.py` | `UserRepository` |

Detalhes: [`use_cases/users/README.md`](use_cases/users/README.md) e [`use_cases/reports/README.md`](use_cases/reports/README.md).

### LoginUseCase

1. Busca o usuário por e-mail; se não existir, lança `UserNotFoundException`.
2. Verifica a senha com `PasswordService.verify`; se falhar, lança `InvalidCredentialsException`.
3. Gera o token com `JwtService.generate_token(user.id, user.email, user.role)`.
4. Devolve `TokenResponse`.

O campo `is_active` do usuário não é verificado no login.

## Padrão de implementação

```python
class GetUserUseCase:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def execute(self, user_id: UUID) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")
        return UserResponse(id=user.id, name=user.name, email=user.email, role=user.role)
```

Regras:

- Um caso de uso por ação, com um único método público `async def execute(...)`.
- Dependências recebidas no construtor, tipadas pelas interfaces do domínio.
- Falhas de negócio sinalizadas com subclasses de `DomainException`.
- Sem imports de `fastapi`, `sqlalchemy` ou `app.infrastructure`.
