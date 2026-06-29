# ⚙️ app/core/

O diretório `core/` centraliza as **configurações globais** da aplicação. Ele fornece um ponto único de acesso a variáveis de ambiente, settings e parâmetros que são compartilhados entre todas as camadas do sistema.

---

## 🗂️ Estrutura

```text
core/
└── config.py         # Definição e carregamento de configurações via variáveis de ambiente
```

---

## 📄 Arquivo: `config.py`

Responsável por carregar e expor todas as **variáveis de ambiente** e configurações da aplicação utilizando **Pydantic Settings**.

### Configurações disponíveis

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Aplicação
    APP_NAME: str = "ApoiaMais Backend"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Banco de Dados
    DATABASE_URL: str

    # Segurança
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 🔧 Variáveis de Ambiente

Todas as variáveis devem ser declaradas no arquivo `.env` na raiz do projeto. Utilize o `.env.example` como referência:

| Variável                       | Descrição                              | Padrão         |
|--------------------------------|----------------------------------------|----------------|
| `APP_NAME`                     | Nome da aplicação                      | ApoiaMais      |
| `APP_ENV`                      | Ambiente de execução                   | `development`  |
| `DEBUG`                        | Modo de depuração                      | `False`        |
| `DATABASE_URL`                 | URL de conexão com o banco de dados    | —              |
| `SECRET_KEY`                   | Chave secreta para assinatura JWT      | —              |
| `ALGORITHM`                    | Algoritmo de criptografia JWT          | `HS256`        |
| `ACCESS_TOKEN_EXPIRE_MINUTES`  | Expiração do token de acesso (minutos) | `30`           |

---

## 📐 Como utilizar

```python
from app.core.config import settings

print(settings.DATABASE_URL)
print(settings.SECRET_KEY)
```

---

## 📋 Boas Práticas

- ❌ Nunca faça commit do arquivo `.env` com credenciais reais
- ✅ Utilize sempre o `.env.example` para documentar as variáveis necessárias
- ✅ Valores sensíveis devem ser injetados via variáveis de ambiente em produção (Docker Secrets, AWS SSM, etc.)
- ✅ Importe `settings` apenas onde necessário — evite dependência circular