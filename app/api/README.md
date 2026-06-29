# 🌐 app/api/

A camada `api/` é a **interface HTTP** da aplicação. Ela é responsável por receber as requisições externas, aplicar validações iniciais, resolver dependências e delegar o processamento aos casos de uso correspondentes.

---

## 🗂️ Estrutura

```text
api/
├── routes/             # Módulos de roteamento por domínio/recurso
├── app.py              # Fábrica e configuração da instância FastAPI
└── dependencies.py     # Provedores de dependências (DI Container)
```

---

## 📄 Arquivos

### `app.py`
Responsável por instanciar e configurar a aplicação **FastAPI**:
- Registro dos roteadores (`include_router`)
- Configuração de middlewares (CORS, autenticação, logging)
- Handlers globais de exceção
- Configuração de metadados da API (título, versão, descrição)

```python
from fastapi import FastAPI
from app.api.routes import users, reports

app = FastAPI(title="ApoiaMais API", version="1.0.0")

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
```

---

### `dependencies.py`
Centraliza a **injeção de dependências** utilizando o sistema nativo do FastAPI (`Depends`):
- Provedor de sessão de banco de dados
- Extração e validação do token JWT
- Injeção de repositórios e serviços nos endpoints

```python
from fastapi import Depends
from app.infrastructure.database import get_db

def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    ...
```

---

### `routes/`
Contém os módulos de rotas organizados por recurso. Cada arquivo define um `APIRouter` com seus respectivos endpoints.

> 📂 Veja: [`routes/README.md`](./routes/README.md)

---

## 🔗 Dependências da Camada

| Importa de            | Motivo                                      |
|-----------------------|---------------------------------------------|
| `application/use_cases/` | Execução dos casos de uso              |
| `core/config.py`      | Acesso a configurações e variáveis globais  |
| `domain/exceptions.py`| Tratamento de exceções de domínio           |

---

## 📐 Convenções

- Cada roteador deve estar em um arquivo separado dentro de `routes/`
- Nenhuma lógica de negócio deve residir nesta camada
- Toda validação de entrada deve ser feita via **Pydantic Schemas**
- Respostas de erro devem seguir o padrão definido nos exception handlers globais