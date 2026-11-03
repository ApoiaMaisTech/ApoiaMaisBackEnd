# app/api/

Camada HTTP do backend. Recebe as requisições, valida o corpo com os DTOs Pydantic, resolve as dependências (sessão do banco, repositórios, serviços, usuário autenticado) e delega o processamento aos casos de uso.

A instância do FastAPI **não** é criada aqui: ela fica em [`../../main.py`](../../main.py), que registra os handlers, o CORS e os routers desta pasta.

## Estrutura

```text
api/
├── app.py                    Arquivo vazio (não utilizado)
├── exception_handlers.py     Conversão de DomainException em resposta HTTP
├── dependencies/
│   ├── auth.py               Autenticação por token Bearer e checagem de role
│   ├── repositories.py       Sessão assíncrona do banco e repositórios
│   ├── services.py           Serviços de senha e JWT usados no login
│   └── use_cases.py          Montagem dos casos de uso
└── routes/
    ├── auth.py               /api/auth
    ├── users.py              /api/users
    └── reports.py            Arquivo vazio (não registrado)
```

## Registro dos routers (`main.py`)

| Prefixo       | Router              | Tag     |
|---------------|---------------------|---------|
| `/api/users`  | `routes/users.py`   | `Users` |
| `/api/auth`   | `routes/auth.py`    | `Auth`  |

Além deles, `main.py` define `GET /` (mensagem simples) e `GET /health`. O `/health` devolve uma resposta fixa e não verifica o banco de dados.

A documentação interativa fica em `/docs` (Swagger UI) e `/redoc`, que o FastAPI gera automaticamente.

## Injeção de dependências

A cadeia de dependências de um caso de uso segue o padrão abaixo:

```text
get_db_session()                         repositories.py  -> AsyncSession por requisição
   └── get_user_repository()             repositories.py  -> SqlUserRepository
          └── get_<acao>_usecase()       use_cases.py     -> caso de uso pronto para a rota
get_password_service()                   services.py      -> PasswordServiceImpl
get_jwt_service()                        services.py      -> JwtServiceImpl (lê settings)
```

A sessão é aberta com `async with AsyncSessionLocal()` e fechada ao fim da requisição. Os commits acontecem dentro do repositório (veja [`../infrastructure/database/README.md`](../infrastructure/database/README.md)).

## Autenticação e autorização (`dependencies/auth.py`)

| Dependência           | Comportamento |
|-----------------------|---------------|
| `get_current_user`    | Lê o header `Authorization: Bearer <token>`, valida assinatura e expiração, **confere o usuário no banco** e devolve um `dict` com `id`, `email` e `role` (o perfil do banco, não o do token). Responde 401 para token ausente, expirado, inválido ou de conta removida. |
| `get_current_teacher` | Exige `role == "teacher"`; caso contrário, responde 403. |
| `get_current_student` | Exige `role == "student"`; caso contrário, responde 403. Não é usada por nenhuma rota no momento. |

O token é conferido contra o banco a cada requisição (busca por chave primária): conta removida perde o acesso na hora e um perfil alterado vale imediatamente, sem esperar o token expirar.

## Tratamento de erros

Todas as respostas de erro usam o formato único `ErrorResponse`
(`success`, `code`, `message`, `errors`, `correlation_id`), produzido pelos handlers de
`exception_handlers.py`:

| Origem | Status | `code` |
|--------|--------|--------|
| `DomainException` | definido na subclasse | definido na subclasse (`USER_NOT_FOUND`...) |
| `ApiError` (`errors.py`) nas dependências de auth, rate limit e rotas | 401, 403, 429 | `UNAUTHORIZED`, `TOKEN_EXPIRED`, `FORBIDDEN`, `RATE_LIMITED`... |
| `HTTPException` do Starlette (rota inexistente, método errado) | 404, 405 | padrão do status |
| Validação do Pydantic | 422 | `VALIDATION_ERROR` |
| `IntegrityError` / outros `SQLAlchemyError` | 409 / 503 | `CONFLICT` / `SERVICE_UNAVAILABLE` |
| Exceção não tratada (capturada no `CorrelationIdMiddleware`) | 500 | `INTERNAL_ERROR` |

Lista completa e regras de validação: [`docs/ERROS.md`](../../docs/ERROS.md).

## CORS

Configurado em `main.py` com origens fixas de desenvolvimento (`localhost` e `127.0.0.1` nas portas 5173, 3000 e 3002), `allow_credentials=True` e todos os métodos e headers liberados. Ainda não é configurável por variável de ambiente.

## Regras da camada

- As rotas não contêm regra de negócio: recebem o DTO, chamam `use_case.execute(...)` e devolvem o resultado.
- Toda implementação concreta (repositório, serviço) é obtida via `Depends`, nunca instanciada dentro da rota.
- Um novo router deve ser registrado em `main.py` com prefixo `/api/<recurso>`.

Detalhes de cada endpoint: [`routes/README.md`](routes/README.md).
