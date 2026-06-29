# 📦 app/

O diretório `app/` é o núcleo da aplicação **ApoiaMais Backend**. Ele concentra toda a lógica de negócio, configurações, domínio e infraestrutura do sistema, seguindo os princípios da **Arquitetura Limpa (Clean Architecture)** e separação de responsabilidades.

---

## 🗂️ Estrutura

```text
app/
├── api/                        # Camada de interface HTTP (rotas e dependências)
│   ├── routes/                 # Definição dos endpoints da aplicação
│   ├── app.py                  # Inicialização e configuração do FastAPI
│   └── dependencies.py         # Injeção de dependências globais
│
├── application/                # Camada de casos de uso (regras de aplicação)
│   └── use_cases/
│       ├── reports/            # Casos de uso relacionados a relatórios
│       └── users/              # Casos de uso relacionados a usuários
│
├── core/                       # Configurações centrais da aplicação
│   └── config.py               # Variáveis de ambiente e settings globais
│
├── domain/                     # Camada de domínio (entidades e exceções)
│   └── exceptions.py           # Exceções customizadas do domínio
│
└── infrastructure/             # Camada de infraestrutura (banco de dados e segurança)
    ├── database/               # Configuração e conexão com o banco de dados
    ├── security/               # Autenticação, autorização e criptografia
    └── main.py                 # Ponto de entrada da aplicação
```

---

## 🏛️ Arquitetura

O módulo `app/` adota os princípios da **Clean Architecture**, dividindo responsabilidades em camadas independentes:

```text
┌─────────────────────────────────────┐
│              api/                   │  ← Interface HTTP (Controllers, Routes)
├─────────────────────────────────────┤
│        application/use_cases/       │  ← Regras de Aplicação (Use Cases)
├─────────────────────────────────────┤
│             domain/                 │  ← Entidades e Regras de Negócio
├─────────────────────────────────────┤
│          infrastructure/            │  ← Banco de Dados, Segurança, I/O
└─────────────────────────────────────┘
│               core/                 │  ← Configurações Transversais
```

> Cada camada depende apenas das camadas internas, nunca das externas — garantindo baixo acoplamento e alta coesão.

---

## ▶️ Ponto de Entrada

A aplicação é inicializada a partir de:

```bash
infrastructure/main.py
```

O arquivo `main.py` é responsável por iniciar o servidor **Uvicorn** e carregar as configurações da aplicação.

---

## 🔗 Relacionamentos entre Camadas

| Camada           | Depende de              | Responsabilidade                         |
|------------------|-------------------------|------------------------------------------|
| `api/`           | `application/`, `core/` | Receber requisições HTTP                 |
| `application/`   | `domain/`               | Orquestrar casos de uso                  |
| `domain/`        | *(nenhuma)*             | Regras de negócio puras                  |
| `infrastructure/`| `domain/`, `core/`      | Persistência, segurança e integrações    |
| `core/`          | *(nenhuma)*             | Configurações e variáveis de ambiente    |