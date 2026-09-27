
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

### Contrato da API

O código deste repositório é a fonte da verdade do contrato da API. Os contratos OpenAPI aprovados ficam no repositório de integração ([ApoiaMaisTech/ApoiaMais](https://github.com/ApoiaMaisTech/ApoiaMais)), em `contratos/<servico>.yaml`, e o frontend gera seus tipos a partir deles. Nenhum contrato é escrito à mão.

Os serviços exportados estão listados em `contratos.json` (nome do contrato, pasta, `modulo:variavel` do app e, opcionalmente, variáveis de ambiente fictícias que o import exige).

**Exportar localmente** (não precisa de MySQL, RabbitMQ nem Redis, e nem de `.env`):

```bash
pip install -r requirements.txt
python scripts/exportar_contratos.py --saida ../ApoiaMais/contratos
```

- `--so auth-service`: exporta apenas os serviços informados.
- `--docker`: exporta dentro do container de cada serviço (`docker compose run --rm --no-deps -T`), útil quando as dependências locais não batem. Requer o `.env` usado pelo `docker-compose.yml`.
- Para exportar um único app: `python scripts/exportar_openapi.py --app main:app --dir . --saida auth-service.yaml` (sem `--saida`, imprime no stdout). Rodando direto, as variáveis exigidas pelo `app/core/config.py` (`DB_USER`, `DB_NAME`, `JWT_SECRET_KEY`) precisam estar no ambiente ou no `.env`; o `exportar_contratos.py` já as preenche com valores fictícios.

**Automação** (`.github/workflows/sync-contrato.yml`): a cada push na `main` que altere o código da API, `contratos.json` ou `scripts/` (ou manualmente, via *Run workflow*), o GitHub Actions exporta os contratos e abre — ou atualiza — um PR no repositório de integração na branch `contrato/sync-backend`, com as labels `contrato` e `automatico` e o link do commit de origem. Se o contrato não mudou, nenhum PR é aberto. O workflow usa um GitHub App (`vars.APP_ID` e `secrets.APP_PRIVATE_KEY`) para que o PR dispare os workflows de validação do repositório de integração.

### Documentação

Toda a documentação do projeto está localizada no diretório `docs/`.

```text
docs/
└── images/
