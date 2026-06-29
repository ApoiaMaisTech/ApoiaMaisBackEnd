# 🛣️ app/api/routes/

O diretório `routes/` contém todos os módulos de **roteamento HTTP** da aplicação, organizados por domínio ou recurso. Cada arquivo define um `APIRouter` do FastAPI responsável por um conjunto específico de endpoints.

---

## 🗂️ Estrutura

```text
routes/
├── users.py          # Endpoints relacionados a usuários
├── reports.py        # Endpoints relacionados a relatórios
└── ...               # Demais recursos da aplicação
```

> Novos recursos devem sempre ser adicionados como um arquivo separado neste diretório e registrados em `app/api/app.py`.

---

## 📐 Padrão de Implementação

Cada módulo de rotas deve seguir a estrutura abaixo:

```python
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_current_user
from app.application.use_cases.users import CreateUserUseCase

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserSchema,
    use_case: CreateUserUseCase = Depends(),
    current_user=Depends(get_current_user),
):
    return use_case.execute(payload)
```

---

## 🔗 Convenções de Endpoints

| Método   | Padrão de Rota       | Ação                        |
|----------|----------------------|-----------------------------|
| `GET`    | `/resource/`         | Listar recursos             |
| `GET`    | `/resource/{id}`     | Buscar recurso por ID       |
| `POST`   | `/resource/`         | Criar novo recurso          |
| `PUT`    | `/resource/{id}`     | Atualizar recurso completo  |
| `PATCH`  | `/resource/{id}`     | Atualizar recurso parcial   |
| `DELETE` | `/resource/{id}`     | Remover recurso             |

---

## 📋 Regras da Camada

- ❌ Nenhuma lógica de negócio deve ser implementada aqui
- ✅ Apenas orquestração: receber → validar schema → chamar use case → retornar resposta
- ✅ Toda autenticação deve ser injetada via `Depends(get_current_user)`
- ✅ Status HTTP deve ser declarado explicitamente via `status_code`
- ✅ Schemas de entrada e saída devem ser **Pydantic models**