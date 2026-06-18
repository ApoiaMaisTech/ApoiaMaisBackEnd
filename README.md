# ApoiaMais

> Plataforma de ensino gamificada para crianças em situação hospitalar.

O **ApoiaMais** é um sistema educacional voltado para crianças internadas em ambientes hospitalares, promovendo continuidade no aprendizado através de uma experiência gamificada, conteúdo gerado por IA e acompanhamento pedagógico em tempo real.

---

## Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Serviços](#serviços)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Configuração](#instalação-e-configuração)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Executando o Projeto](#executando-o-projeto)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Contribuindo](#contribuindo)
- [Licença](#licença)
- [Contribuidores](#contribuidores)

---

## Sobre o Projeto

Crianças hospitalizadas frequentemente ficam afastadas da escola por longos períodos, gerando defasagem escolar e impacto emocional. O **ApoiaMais** preenche essa lacuna oferecendo uma experiência de aprendizado gamificada, com conteúdo adaptado gerado por inteligência artificial, acompanhamento de progresso pedagógico e notificações em tempo real — tudo pensado para o contexto hospitalar.

---

## Funcionalidades

- Interface gamificada com elementos lúdicos para engajar crianças
- Autenticação segura via Auth Service dedicado
- Perfil do paciente com dados pedagógicos e hospitalares centralizados
- Acompanhamento de progresso pedagógico e conquistas
- Host de jogos e atividades com cache via Redis
- Geração de histórias e imagens personalizadas com OpenAI/Gemini
- Notificações em tempo real de badges e feedback emocional via WebSocket
- Mensageria assíncrona com eventos desacoplados via RabbitMQ

---

## Arquitetura

O ApoiaMais é construído sobre uma arquitetura de **microsserviços**, com comunicação síncrona via HTTP/REST e assíncrona via RabbitMQ.

```
React Frontend (Gamificado)
         │
         │ HTTP/REST & WebSockets
         ▼
    API Gateway
    ┌──────────────────────────────────────────────────────┐
    │  Auth     Patient   Pedagogical   Ludic     AI       │
    │  Service  Profile   Progress      Host      Service  │
    │           Service   Service       Service   (FastAPI)│
    └──────────────────────────────────────────────────────┘
         │         │            │          │         │
         │         ▼            │          ▼         ▼
         │    PostgreSQL        │        Redis    OpenAI /
         │                      │                  Gemini
         │              ┌───────┘
         │              ▼
         │          RabbitMQ ──────────────────────────────┐
         │              │                                  │
         │              ▼                                  ▼
         │         AI Service                   Notification Service
         │       (consome eventos)                         │
         │                                                 │ WebSocket
         └─────────────────────────────────────────────────┘
                                                    React Frontend
```

---

## Serviços

**API Gateway** — roteamento, autenticação de entrada e rate limiting via HTTP/REST.

**Auth Service** — login, registro, emissão e renovação de tokens JWT.

**Patient Profile Service** — perfil do paciente e dados hospitalares, persistidos em PostgreSQL.

**Pedagogical Progress Service** — progresso pedagógico e conquistas, com emissão de eventos via RabbitMQ para PostgreSQL.

**Ludic Host Service** — jogos e atividades lúdicas com estado armazenado em Redis.

**Generative AI Service** — geração de histórias e imagens via LLM, consumindo eventos do RabbitMQ e chamando OpenAI/Gemini.

**Notification Service** — entrega de badges e feedback emocional em tempo real, consumindo eventos do RabbitMQ e enviando via WebSocket.

---

## Tecnologias

- **Frontend:** React (Gamificado)
- **API Gateway:** a definir (Nginx, Kong ou serviço custom)
- **Backend:** Python + FastAPI
- **Banco de Dados:** PostgreSQL
- **Cache:** Redis
- **Mensageria:** RabbitMQ
- **IA Generativa:** OpenAI API / Google Gemini
- **Comunicação:** HTTP/REST + WebSockets
- **Containerização:** Docker / Docker Compose

---

## Pré-requisitos

- [Python 3.11+](https://www.python.org/)
- [Node.js 18+](https://nodejs.org/)
- [Docker](https://www.docker.com/) e [Docker Compose](https://docs.docker.com/compose/)
- [Git](https://git-scm.com/)

---

## Instalação e Configuração

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/apoiamais.git
cd apoiamais

# 2. Configure as variáveis de ambiente
cp .env.example .env

# 3. Suba toda a infraestrutura
docker-compose up --build
```

Os serviços estarão disponíveis conforme mapeado no `docker-compose.yml`.

---

## Variáveis de Ambiente

Cada serviço possui seu próprio `.env`. O `.env.example` na raiz documenta todas as variáveis necessárias:

```env
# Auth Service
SECRET_KEY=sua_chave_secreta
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Banco de Dados
DB_HOST=postgres
DB_PORT=5432
DB_USER=apoiamais
DB_PASSWORD=sua_senha
DB_NAME=apoiamais

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Redis
REDIS_URL=redis://redis:6379

# IA Generativa
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

> Nunca commite arquivos `.env` com credenciais reais.

---

## Executando o Projeto

```bash
# Subir todos os serviços
docker-compose up

# Subir um serviço específico
docker-compose up ai-service

# Ver logs de um serviço
docker-compose logs -f notification-service
```

---

## Estrutura de Pastas


---

## Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/minha-feature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona minha feature'`)
4. Push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

Siga o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/).

---

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## Contribuidores

Agradecimento especial a todas as pessoas incríveis que contribuíram para este projeto.

<a href=">
  <img src=" />
</a>

---

*ApoiaMais — porque aprender não para, mesmo no hospital.*﻿
