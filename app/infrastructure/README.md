# 🏗️ app/infrastructure/

O diretório `infrastructure/` contém a **camada de infraestrutura** da aplicação. É aqui que residem todos os detalhes técnicos externos: conexões com banco de dados, mecanismos de autenticação e segurança, integrações com serviços externos e o ponto de entrada do servidor.

Esta camada é a única que conhece e depende de tecnologias específicas como **SQLAlchemy**, **JWT**, **Redis** e outras.

---

## 🗂️ Estrutura

```text
infrastructure/
├── database/           # Configuração do banco de dados e repositórios
├── security/           # Autenticação JWT e utilitários de segurança
└── main.py             # Ponto de entrada da aplicação (Uvicorn)
```

---

## 📄 Arquivo: `main.py`

Ponto de entrada da aplicação. Responsável por inicializar o servidor **Uvicorn** com as configurações definidas em `core/config.py`.

```python
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
```

---

## 📂 Subdiretórios

### `database/`
Configuração de conexão, sessão e repositórios do banco de dados.

> 📂 Veja: [`database/README.md`](./database/README.md)

---

### `security/`
Utilitários de autenticação e autorização: geração/validação de tokens JWT e hashing de senhas.

> 📂 Veja: [`security/README.md`](./security/README.md)

---

## 🔗 Dependências da Camada

| Importa de          | Motivo                                       |
|---------------------|----------------------------------------------|
| `core/config.py`    | Variáveis de ambiente e configurações        |
| `domain/`           | Entidades de domínio para mapeamento ORM     |

---

## 📋 Princípios desta Camada

- ✅ Única camada com acesso a bibliotecas de terceiros (SQLAlchemy, JWT, etc.)
- ✅ Repositórios devem implementar interfaces definidas no domínio
- ❌ Nenhuma regra de negócio deve residir aqui
- ❌ Não importe diretamente de `api/` ou `application/`