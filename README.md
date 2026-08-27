
# ApoiaMais Backend

O **ApoiaMais Backend** é uma plataforma educacional baseada em **Arquitetura de Microsserviços**, desenvolvida para oferecer uma solução escalável para gerenciamento de usuários, atividades educacionais, geração de histórias, imagens utilizando inteligência artificial e demais recursos da plataforma.

O sistema foi desenvolvido utilizando **Python**, **FastAPI**, **MySQL**, **RabbitMQ**, **Redis** e **Docker**, adotando uma **Arquitetura de Microsserviços**, onde cada serviço possui uma responsabilidade específica, seu próprio banco de dados e comunicação independente, proporcionando maior escalabilidade, organização e facilidade de manutenção.

<img src="./docs/images/demo.gif" />

---

### Estrutura do Projeto

```text
ApoiaMaisBackend/
├── api-gateway/
├── app/
│   ├── api/
│   ├── application/
│   ├── core/
│   ├── domain/
│   └── infrastructure/
├── docs/
│   └── images/
├── .gitignore
├── docker-compose.yml
├── README.md
└── requirements.txt
```

### Clonar o repositório

```bash
git clone https://github.com/seu-usuario/apoiamais-backend.git

cd apoiamais-backend
```

### Iniciar os serviços

```bash
docker compose up --build
```
### Cada microsserviço segue a mesma organização interna.

```text
controllers/
services/
repositories/
models/
routes/
schemas/
config/
database/
utils/
```

---

### Fluxo da Aplicação

```text
Cliente
    │
    ▼
API Gateway
    │
    ├────────► Auth Service
    ├────────► User Service
    ├────────► Ludic Service
    ├────────► File Service
    ├────────► Notification Service
    ├────────► Report Service
    └────────► Audit Service
```

### Documentação

Toda a documentação do projeto está localizada no diretório `docs/`.

```text
docs/
└── images/
