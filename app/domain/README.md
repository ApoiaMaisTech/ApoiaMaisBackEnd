# 🏛️ app/domain/

O diretório `domain/` representa a **camada de domínio** da aplicação — o núcleo da Clean Architecture. Aqui residem as **entidades**, **regras de negócio puras** e **exceções de domínio**, completamente isoladas de frameworks, banco de dados e detalhes de infraestrutura.

---

## 🗂️ Estrutura

```text
domain/
└── exceptions.py         # Exceções customizadas de domínio
```

---

## 📄 Arquivo: `exceptions.py`

Define todas as **exceções customizadas** do sistema, organizadas por domínio. Estas exceções representam cenários de negócio inválidos e são lançadas pelos casos de uso para sinalizar falhas específicas.

### Estrutura das Exceções

```python
class ApoiaMaisException(Exception):
    """Exceção base da aplicação."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ── Usuários ─────────────────────────────────────
class UserNotFoundException(ApoiaMaisException):
    def __init__(self, user_id: int):
        super().__init__(f"Usuário com ID {user_id} não encontrado.", status_code=404)

class EmailAlreadyExistsException(ApoiaMaisException):
    def __init__(self, email: str):
        super().__init__(f"O e-mail '{email}' já está em uso.", status_code=409)

class InvalidCredentialsException(ApoiaMaisException):
    def __init__(self):
        super().__init__("Credenciais inválidas.", status_code=401)


# ── Relatórios ────────────────────────────────────
class ReportNotFoundException(ApoiaMaisException):
    def __init__(self, report_id: int):
        super().__init__(f"Relatório com ID {report_id} não encontrado.", status_code=404)


# ── Autorização ───────────────────────────────────
class UnauthorizedException(ApoiaMaisException):
    def __init__(self):
        super().__init__("Acesso não autorizado.", status_code=403)
```

---

## 📋 Catálogo de Exceções

### Usuários

| Exceção                       | Status | Descrição                                   |
|-------------------------------|--------|---------------------------------------------|
| `UserNotFoundException`       | 404    | Usuário não encontrado pelo ID              |
| `EmailAlreadyExistsException` | 409    | E-mail já cadastrado na plataforma          |
| `InvalidCredentialsException` | 401    | Credenciais de login inválidas              |
| `InvalidUserDataException`    | 422    | Dados do usuário com formato inválido       |

### Relatórios
>
| Exceção                       | Status | Descrição                                   |
|-------------------------------|--------|---------------------------------------------|
| `ReportNotFoundException`     | 404    | Relatório não encontrado pelo ID            |
| `UnsupportedFormatException`  | 400    | Formato de exportação não suportado         |

### Autorização

| Exceção                       | Status | Descrição                                   |
|-------------------------------|--------|---------------------------------------------|
| `UnauthorizedException`       | 403    | Usuário sem permissão para a ação           |

---

## 🔗 Integração com a API

As exceções de domínio são capturadas pelos **exception handlers** registrados em `app/api/app.py` e convertidas automaticamente em respostas HTTP padronizadas:

```json
{
  "detail": "Usuário com ID 42 não encontrado.",
  "status_code": 404
}
```

---

## 📐 Princípios desta Camada

- ✅ **Zero dependências externas** — nenhuma importação de FastAPI, SQLAlchemy ou bibliotecas de terceiros
- ✅ Exceções com mensagens descritivas e status HTTP semânticos
- ✅ Hierarquia clara com uma exceção base (`ApoiaMaisException`)
- ❌ Nunca acesse banco de dados ou camadas externas a partir do domínio