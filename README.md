# ApoiaMais Backend

[🇧🇷 Português](./README.pt-BR.md)

**ApoiaMais Backend** is the backend application for the ApoiaMais educational platform, providing APIs for authentication, user management, reports, authorization, and other core platform features.

The project is built with **Python and FastAPI**, following **Clean Architecture** principles to keep business rules independent from frameworks, databases, and infrastructure concerns.

<img src="./docs/images/demo.gif" />

## Features

* RESTful API built with FastAPI
* JWT-based authentication
* Role-based authorization
* User management
* Reports API
* Password hashing and secure credential handling
* IP-based rate limiting
* MySQL persistence with SQLAlchemy
* Database migrations with Alembic
* Redis integration for distributed rate limiting
* Standardized API error responses
* Unit and integration tests
* OpenAPI contract generation
* Automated contract synchronization
* Docker and Docker Compose support
* GitHub Actions CI

## Architecture

The application follows a layered architecture inspired by **Clean Architecture**:

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

The API layer contains the FastAPI application, HTTP routes, dependencies, authentication dependencies, rate limiting, and exception handlers.

### Application

The application layer contains the use cases and DTOs used to orchestrate application behavior without coupling business logic directly to HTTP or infrastructure.

### Domain

The domain layer contains the core business rules, entities, repository abstractions, domain services, enums, and business exceptions.

### Infrastructure

The infrastructure layer contains concrete implementations for database access, security, JWT handling, password hashing, and rate limiting.

## Project Structure

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

## Tech Stack

| Technology     | Purpose                        |
| -------------- | ------------------------------ |
| Python         | Backend development            |
| FastAPI        | REST API                       |
| SQLAlchemy     | ORM and database access        |
| Alembic        | Database migrations            |
| MySQL          | Relational database            |
| Redis          | Rate limiting and shared state |
| JWT            | Authentication                 |
| Docker         | Containerization               |
| Pytest         | Automated testing              |
| GitHub Actions | CI and automation              |
| OpenAPI        | API contracts                  |

## Getting Started

### Requirements

* Python 3.12+
* Docker
* Docker Compose
* Git

### Clone the repository

```bash
git clone https://github.com/ApoiaMaisTech/ApoiaMaisBackEnd.git

cd ApoiaMaisBackEnd
```

### Configure the environment

Create your local environment file:

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

### Run with Docker

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up --build -d
```

View the application logs:

```bash
docker compose logs -f
```

Stop the environment:

```bash
docker compose down
```

## Local Development

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative documentation:

```text
http://127.0.0.1:8000/redoc
```

## Authentication & Authorization

Authentication is implemented using **JWT tokens**.

Protected routes validate the authenticated user and enforce the required role before executing the corresponding use case.

The main authentication components are located in:

```text
app/
├── api/dependencies/auth.py
├── application/use_cases/auth/
├── domain/services/jwt_service.py
└── infrastructure/security/jwt.py
```

## Rate Limiting

The API includes IP-based rate limiting to protect sensitive endpoints.

The main implementation is located in:

```text
app/api/dependencies/rate_limit.py
app/infrastructure/rate_limit.py
```

When Redis is configured, rate-limit counters can be shared between application processes.

When Redis is not configured, the application falls back to in-memory storage.

When a limit is exceeded, the API returns:

```http
429 Too Many Requests
```

with the `Retry-After` header.

## Error Handling

API errors follow a standardized response format:

```json
{
  "success": false,
  "message": "Error message",
  "errors": []
}
```

Domain exceptions are defined separately from HTTP handling:

```text
app/domain/exceptions/
```

and mapped to API responses through:

```text
app/api/exception_handlers.py
```

## Database

The project uses **MySQL** with SQLAlchemy.

Database infrastructure is organized as:

```text
app/infrastructure/database/
├── base.py
├── mappers/
├── models/
├── repositories/
├── mixins.py
└── session.py
```

Database schema changes are managed with **Alembic**.

```text
app/alembic/
└── versions/
```

Apply migrations with:

```bash
alembic upgrade head
```

## Testing

The project includes both unit and integration tests.

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

Run the complete test suite:

```bash
pytest
```

Run unit tests:

```bash
pytest tests/unit
```

Run integration tests:

```bash
pytest tests/integration
```

Run the authorization matrix:

```bash
pytest tests/integration/api/test_authorization_matrix.py
```

## API Contracts

The backend source code is the source of truth for the API contracts.

OpenAPI contracts are generated automatically and synchronized with the ApoiaMais integration repository.

Contract configuration is defined in:

```text
contratos.json
```

Export all contracts:

```bash
python scripts/exportar_contratos.py \
  --saida ../ApoiaMais/contratos
```

Export a specific service:

```bash
python scripts/exportar_contratos.py \
  --so auth-service
```

Export using Docker:

```bash
python scripts/exportar_contratos.py --docker
```

A single OpenAPI application can also be exported with:

```bash
python scripts/exportar_openapi.py \
  --app main:app \
  --dir . \
  --saida api.yaml
```

## CI & Automation

GitHub Actions workflows are located in:

```text
.github/workflows/
├── ci.yml
└── sync-contrato.yml
```

### Continuous Integration

`ci.yml` runs the project's automated validation and test pipeline.

### Contract Synchronization

`sync-contrato.yml` automatically exports API contracts when relevant backend changes are pushed to `main`.

When a contract changes, the workflow creates or updates the corresponding Pull Request in the integration repository.

```text
Backend change
      │
      ▼
GitHub Actions
      │
      ▼
OpenAPI generation
      │
      ▼
Contract comparison
      │
      ├── No changes
      │
      └── Changes detected
              │
              ▼
        Integration PR
```

## First Teacher

User creation for protected flows requires an authenticated teacher.

The first teacher can be created using the project script:

```bash
python scripts/criar_usuario.py \
  --role teacher \
  --nome "Professor" \
  --email professor@exemplo.dev \
  --senha "uma-senha-forte"
```

When running inside Docker, execute the command from the appropriate application container defined in `docker-compose.yml`.

## Documentation

Additional project documentation is available in:

```text
docs/
├── README.md
└── images/
```

API documentation is automatically provided by FastAPI through Swagger UI and ReDoc.

## License

This project is licensed under the terms defined in the [LICENSE](./LICENSE) file.

## ApoiaMais

ApoiaMais is an educational technology platform designed to support learning experiences through technology, interactive resources, and intelligent educational tools.
