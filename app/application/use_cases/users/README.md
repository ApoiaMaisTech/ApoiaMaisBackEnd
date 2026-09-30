# app/application/use_cases/users/

Casos de uso do CRUD de usuários. Todos recebem as dependências pelo construtor e são montados em [`app/api/dependencies/use_cases.py`](../../../api/dependencies/use_cases.py).

## Arquivos

| Arquivo                   | Classe              | Estado |
|---------------------------|---------------------|--------|
| `create_user_usecase.py`  | `CreateUserUseCase` | Em uso |
| `get_user_usecase.py`     | `GetUserUseCase`    | Em uso |
| `list_user_usecase.py`    | `ListUserUseCase`   | Em uso |
| `update_user_usecase.py`  | `UpdateUserUseCase` | Em uso |
| `delete_user_usecase.py`  | `DeleteUserUseCase` | Em uso |
| `delete_user.py`          | `DeleteUserUseCase` | Versão antiga duplicada, não referenciada |

## Comportamento

### CreateUserUseCase

`execute(request: CreateUserRequest, role: UserRole) -> UserResponse`

1. Consulta `get_by_email`; se o e-mail já existe, lança `EmailAlreadyExistsException`.
2. Gera o hash da senha com `PasswordService.hash`.
3. Cria a entidade `User` com a role recebida da rota (`STUDENT` ou `TEACHER`) e persiste com `repository.create`.

A verificação de e-mail e a inserção não são atômicas. Em requisições simultâneas, a restrição `UNIQUE` do banco é quem impede a duplicidade, e o erro resultante não é tratado (retorna 500).

### GetUserUseCase

`execute(user_id: UUID) -> UserResponse`. Lança `UserNotFoundException` se o usuário não existe.

### ListUserUseCase

`execute() -> list[UserResponse]`. Retorna todos os usuários, sem paginação nem filtros.

### UpdateUserUseCase

`execute(user_id: UUID, request: UpdateUserRequest) -> UserResponse`

1. Lança `UserNotFoundException` se o usuário não existe.
2. Lança `EmailAlreadyExistsException` se o novo e-mail pertence a outro usuário.
3. Substitui e-mail e hash de senha e persiste com `repository.update`.

Não altera o nome nem a role, e não exige a senha atual.

### DeleteUserUseCase

`execute(user_id) -> UserResponse`. Lança `UserNotFoundException` se o usuário não existe e remove o registro fisicamente. A rota responde 204 e descarta o retorno.

## Testes

Cobertos por [`tests/unit/use_cases/users/test_user_usecases.py`](../../../../tests/unit/use_cases/users/test_user_usecases.py), com o repositório e o serviço de senha substituídos por mocks.
