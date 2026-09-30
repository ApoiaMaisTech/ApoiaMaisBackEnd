# app/api/routes/

Routers HTTP da aplicação. Cada arquivo define um `APIRouter` que é registrado em [`../../../main.py`](../../../main.py) com seu prefixo.

## Arquivos

| Arquivo      | Prefixo      | Estado |
|--------------|--------------|--------|
| `auth.py`    | `/api/auth`  | Implementado |
| `users.py`   | `/api/users` | Implementado |
| `reports.py` | —            | Vazio, não registrado em `main.py` |

## Endpoints

### Autenticação (`auth.py`)

| Método | Rota              | Autenticação | Corpo          | Resposta |
|--------|-------------------|--------------|----------------|----------|
| POST   | `/api/auth/login` | Pública      | `LoginRequest` (`email`, `password`) | 200 `TokenResponse`; 404 se o e-mail não existe; 401 se a senha está errada |

Formato de `TokenResponse`:

```json
{
  "token": "<jwt>",
  "user": { "id": "<uuid>", "name": "...", "email": "...", "role": "teacher" }
}
```

O token JWT (HS256 por padrão) carrega as claims `user_id`, `user_email`, `role` e `exp`. A resposta ainda não inclui `patientId` para alunos, campo exigido pelo frontend no login de aluno.

### Usuários (`users.py`)

| Método | Rota                     | Autenticação         | Corpo               | Resposta |
|--------|--------------------------|----------------------|---------------------|----------|
| POST   | `/api/users/students`    | Pública              | `CreateUserRequest` | 200 `UserResponse` com role `student` |
| POST   | `/api/users/teachers`    | Pública              | `CreateUserRequest` | 200 `UserResponse` com role `teacher` |
| GET    | `/api/users/`            | Bearer, role teacher | —                   | 200 `list[UserResponse]` (sem paginação) |
| GET    | `/api/users/{user_id}`   | Nenhuma              | —                   | 200 `UserResponse` |
| PUT    | `/api/users/{user_id}`   | Nenhuma              | `UpdateUserRequest` (`email`, `password`) | 200 `UserResponse` |
| DELETE | `/api/users/{user_id}`   | Nenhuma              | —                   | 204 sem corpo (remoção física) |

`CreateUserRequest`: `name` (3 a 100 caracteres), `email` (validado como e-mail) e `password` (mínimo de 8 caracteres).

Erros de domínio nessas rotas (`UserNotFoundException`, `EmailAlreadyExistsException`) passam pelo handler global e retornam **400**. Veja [`../README.md`](../README.md#tratamento-de-erros).

Somente `GET /api/users/` declara `response_model`. Nas demais rotas o schema de resposta aparece vazio no contrato OpenAPI exportado.

## Situação de segurança

As rotas `GET`, `PUT` e `DELETE /api/users/{user_id}` e a criação de professores não exigem autenticação. Essa é uma limitação conhecida do estado atual e precisa ser resolvida antes de qualquer uso com dados reais.

## Padrão para novas rotas

```python
from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_teacher
from app.api.dependencies.use_cases import get_create_user_usecase
from app.application.dto.create_user_request import CreateUserRequest
from app.application.dto.create_user_response import UserResponse
from app.application.use_cases.users.create_user_usecase import CreateUserUseCase

router = APIRouter()


@router.post("/students", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    request: CreateUserRequest,
    current_teacher=Depends(get_current_teacher),
    use_case: CreateUserUseCase = Depends(get_create_user_usecase),
):
    ...
```

Recomendações:

- Declarar `response_model` e `status_code` em toda rota, para que o contrato OpenAPI saia completo.
- Proteger toda rota que não seja explicitamente pública com uma dependência de autenticação.
- Manter a rota fina: validação de entrada pelo DTO e regra de negócio no caso de uso.
- Registrar o router em `main.py` com prefixo `/api/<recurso>`.
