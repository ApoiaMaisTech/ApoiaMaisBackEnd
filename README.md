# ApoiaMais Backend

    

O **ApoiaMais Backend** é o backend da plataforma educacional ApoiaMais, responsável por fornecer APIs para autenticação, gerenciamento de usuários, relatórios, autorização e outros recursos fundamentais da plataforma.

O projeto foi desenvolvido utilizando **Python e FastAPI**, seguindo princípios de **Clean Architecture**, separação de responsabilidades e baixo acoplamento entre regras de negócio, banco de dados e infraestrutura.

<img src="./docs/images/demo.gif" />

## Funcionalidades

* API RESTful desenvolvida com FastAPI
* Autenticação baseada em JWT
* Autorização baseada em funções
* Gerenciamento de usuários
* API de relatórios
* Hash seguro de senhas
* Rate limiting baseado em IP
* Persistência com MySQL e SQLAlchemy
* Migrations de banco de dados com Alembic
* Redis para rate limiting distribuído
* Respostas de erro padronizadas
* Testes unitários e de integração
* Geração de contratos OpenAPI
* Sincronização automática de contratos
* Execução através de Docker e Docker Compose
* Integração contínua com GitHub Actions

## Arquitetura

A aplicação segue uma arquitetura em camadas inspirada nos princípios de **Clean Architecture**:

```text
app/
├── api/
│   ├── dependencies/
│   └── routes/
│
├── application/
│   ├── common/
│   ├── dto/
│   └── use_cases/
│
├── core/
│
├── domain/
│   ├── entities/
│   ├── enums/
│   ├── exceptions/
│   ├── repositories/
│   └── services/
│
└── infrastructure/
    ├── database/
    ├── rate_limit.py
    └── security/
```

### API

A camada de API contém a aplicação FastAPI, rotas HTTP, dependências, autenticação, rate limiting e tratamento de exceções.

### Application

A camada de aplicação contém os casos de uso e DTOs responsáveis por orquestrar as operações do sistema, sem acoplamento direto com HTTP ou infraestrutura.

### Domain

A camada de domínio contém as principais regras de negócio, entidades, contratos de repositórios, serviços, enums e exceções específicas do domínio.

### Infrastructure

A camada de infraestrutura contém as implementações concretas utilizadas pela aplicação, incluindo banco de dados, segurança, JWT, hashing de senhas e rate limiting.

## Estrutura do Projeto

```text
ApoiaMaisBackEnd/
├── app/
│   ├── alembic/
│   ├── api/
│   ├── application/
│   ├── core/
│   ├── domain/
│   └── infrastructure/
│
├── docs/
│   └── images/
│
├── scripts/
│   ├── criar_usuario.py
│   ├── exportar_contratos.py
│   └── exportar_openapi.py
│
├── tests/
│   ├── integration/
│   └── unit/
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── sync-contrato.yml
│
├── contratos.json
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.db
├── .env.example
├── init_db.sh
├── main.py
├── pytest.ini
└── requirements.txt
```

## Tecnologias

| Tecnologia     | Utilização                                  |
| -------------- | ------------------------------------------- |
| Python         | Desenvolvimento do backend                  |
| FastAPI        | API REST                                    |
| SQLAlchemy     | ORM e acesso ao banco                       |
| Alembic        | Migrations                                  |
| MySQL          | Banco de dados relacional                   |
| Redis          | Rate limiting e armazenamento compartilhado |
| JWT            | Autenticação                                |
| Docker         | Containerização                             |
| Pytest         | Testes automatizados                        |
| GitHub Actions | CI e automações                             |
| OpenAPI        | Contratos da API                            |

## Primeiros Passos

### Requisitos

* Python 3.12+
* Docker
* Docker Compose
* Git

### Clonar o repositório

```bash
git clone https://github.com/ApoiaMaisTech/ApoiaMaisBackEnd.git

cd ApoiaMaisBackEnd
```

### Configurar o ambiente

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Configure as variáveis necessárias no arquivo `.env`.

### Executar com Docker

```bash
docker compose up --build
```

Para executar em segundo plano:

```bash
docker compose up --build -d
```

Para visualizar os logs:

```bash
docker compose logs -f
```

Para parar o ambiente:

```bash
docker compose down
```

## Desenvolvimento Local

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute a aplicação:

```bash
uvicorn main:app --reload
```

A API estará disponível em:

```text
http://127.0.0.1:8000
```

Documentação interativa:

```text
http://127.0.0.1:8000/docs
```

Documentação alternativa:

```text
http://127.0.0.1:8000/redoc
```

## Autenticação e Autorização

A autenticação da aplicação utiliza **JSON Web Tokens (JWT)**.

As rotas protegidas validam o usuário autenticado e verificam as permissões necessárias antes da execução dos casos de uso.

Os principais componentes estão localizados em:

```text
app/
├── api/dependencies/auth.py
├── application/use_cases/auth/
├── domain/services/jwt_service.py
└── infrastructure/security/jwt.py
```

## Rate Limiting

A API possui rate limiting baseado em IP para proteger endpoints contra excesso de requisições.

A implementação está localizada em:

```text
app/api/dependencies/rate_limit.py
app/infrastructure/rate_limit.py
```

Quando o Redis está configurado, os contadores podem ser compartilhados entre diferentes processos da aplicação.

Caso o Redis não esteja configurado, o sistema utiliza armazenamento em memória.

Quando o limite é excedido, a API retorna:

```http
429 Too Many Requests
```

juntamente com o cabeçalho:

```http
Retry-After
```

## Tratamento de Erros

As respostas de erro da API seguem um formato padronizado:

```json
{
  "success": false,
  "message": "Mensagem do erro",
  "errors": []
}
```

As exceções específicas do domínio estão separadas das exceções HTTP:

```text
app/domain/exceptions/
```

O tratamento das exceções da API é centralizado em:

```text
app/api/exception_handlers.py
```

## Banco de Dados

O projeto utiliza **MySQL** com **SQLAlchemy**.

A infraestrutura de persistência está organizada em:

```text
app/infrastructure/database/
├── base.py
├── mappers/
├── models/
├── repositories/
├── mixins.py
└── session.py
```

As alterações do schema são controladas através do **Alembic**:

```text
app/alembic/
└── versions/
```

Para aplicar as migrations:

```bash
alembic upgrade head
```

## Testes

O projeto possui testes unitários e de integração.

```text
tests/
├── integration/
│   ├── api/
│   └── repositories/
│
└── unit/
    ├── use_cases/
    └── test_rate_limiter_storage.py
```

Executar todos os testes:

```bash
pytest
```

Executar somente os testes unitários:

```bash
pytest tests/unit
```

Executar os testes de integração:

```bash
pytest tests/integration
```

Executar a matriz de autorização:

```bash
pytest tests/integration/api/test_authorization_matrix.py
```

## Contratos da API

O código do backend é a fonte da verdade dos contratos da API.

Os contratos OpenAPI são gerados automaticamente e sincronizados com o repositório de integração do ApoiaMais.

A configuração dos contratos está em:

```text
contratos.json
```

Para exportar todos os contratos:

```bash
python scripts/exportar_contratos.py \
  --saida ../ApoiaMais/contratos
```

Para exportar um contrato específico:

```bash
python scripts/exportar_contratos.py \
  --so auth-service
```

Para realizar a exportação utilizando Docker:

```bash
python scripts/exportar_contratos.py --docker
```

Também é possível exportar um único aplicativo:

```bash
python scripts/exportar_openapi.py \
  --app main:app \
  --dir . \
  --saida api.yaml
```

## CI e Automação

As automações do projeto utilizam **GitHub Actions**:

```text
.github/workflows/
├── ci.yml
└── sync-contrato.yml
```

### Integração Contínua

O workflow `ci.yml` executa as validações automatizadas e os testes do projeto.

### Sincronização dos Contratos

O workflow `sync-contrato.yml` automatiza a geração e sincronização dos contratos OpenAPI.

O fluxo funciona da seguinte maneira:

```text
Alteração no backend
        │
        ▼
GitHub Actions
        │
        ▼
Geração dos contratos OpenAPI
        │
        ▼
Verificação de alterações
        │
        ├── Sem alteração
        │
        └── Contrato alterado
                │
                ▼
        Pull Request no
        repositório de integração
```

## Primeiro Professor

Alguns fluxos de cadastro exigem um professor autenticado.

O primeiro professor pode ser criado utilizando o script:

```bash
python scripts/criar_usuario.py \
  --role teacher \
  --nome "Professor" \
  --email professor@exemplo.dev \
  --senha "uma-senha-forte"
```

Quando executado através do Docker, utilize o container correspondente definido no `docker-compose.yml`.

## Documentação

A documentação adicional do projeto está disponível em:

```text
docs/
├── README.md
└── images/
```

A documentação da API é gerada automaticamente pelo FastAPI através do Swagger UI e ReDoc.

## Licença

Este projeto está licenciado sob a **Licença MIT**.

Consulte o arquivo [LICENSE](./LICENSE) para obter o texto completo da licença.
