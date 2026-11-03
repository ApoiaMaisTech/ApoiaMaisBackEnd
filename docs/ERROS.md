# Erros da API

Toda resposta de erro (4xx e 5xx) tem o mesmo formato, descrito no contrato
OpenAPI como `ErrorResponse`:

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "Dados inválidos.",
  "errors": ["email: value is not a valid email address"],
  "correlation_id": "4f9c2b7e1a3d4c5b8e6f7a8b9c0d1e2f"
}
```

| Campo | Uso |
|---|---|
| `code` | **Contrato estável.** O frontend decide o que fazer por ele (ex.: `TOKEN_EXPIRED` → mandar para o login). |
| `message` | Texto em português para exibir. Pode mudar sem aviso; não compare strings. |
| `errors` | Um item por campo inválido (`"campo: problema"`), só em `VALIDATION_ERROR`. O valor enviado nunca é ecoado (pode ser senha). |
| `correlation_id` | Igual ao header `X-Correlation-ID`; use para achar a requisição nos logs da API e dos workers. |

Nenhum erro expõe traceback, SQL, nome de tabela ou mensagem de biblioteca.

## Códigos

| Status | `code` | Quando |
|---|---|---|
| 400 | `BAD_REQUEST` | Requisição inválida genérica |
| 401 | `UNAUTHORIZED` | Sem header `Authorization: Bearer` |
| 401 | `TOKEN_INVALID` | Token malformado, assinatura inválida, role ou id desconhecidos |
| 401 | `TOKEN_EXPIRED` | Token expirado (refazer login) |
| 401 | `INVALID_CREDENTIALS` | Login com email ou senha errados (mesma resposta nos dois casos) |
| 403 | `FORBIDDEN` | Perfil sem permissão ou recurso de outro usuário |
| 404 | `NOT_FOUND` | Rota inexistente |
| 404 | `USER_NOT_FOUND`, `STAGE_NOT_FOUND`, `AI_IMAGE_NOT_FOUND` | Recurso não existe |
| 405 | `METHOD_NOT_ALLOWED` | Método HTTP não suportado na rota |
| 409 | `EMAIL_ALREADY_EXISTS` | Email já cadastrado (sem diferenciar maiúsculas) |
| 409 | `AI_IMAGE_NOT_READY` | Imagem ainda em geração |
| 409 | `CONFLICT` | Violação de integridade no banco (corrida entre requisições) |
| 422 | `VALIDATION_ERROR` | Corpo, query ou path fora do esperado, inclusive JSON malformado |
| 429 | `RATE_LIMITED` | Limite de requisições (veja `Retry-After`) |
| 429 | `AI_IMAGE_QUOTA_EXCEEDED` | Cota diária de ilustrações |
| 500 | `INTERNAL_ERROR` | Erro inesperado (logado com traceback e correlation id) |
| 503 | `SERVICE_UNAVAILABLE` | Banco indisponível |

## Validação de entrada

Regras compartilhadas em `app/application/dto/validators.py`:

- **Email**: espaços nas pontas removidos e convertido para minúsculas (criação, atualização e login).
- **Nome**: espaços nas pontas removidos, espaços repetidos colapsados, 3 a 100 caracteres, sem caracteres de controle.
- **Senha nova**: 8 a 128 caracteres, **sem** normalização (espaços fazem parte da senha).
- **Login**: senha de 1 a 128 caracteres (o limite evita hash PBKDF2 de payloads enormes).
- Campos extras no corpo são ignorados. O cargo vem sempre da rota (`/students`, `/teachers`),
  nunca do corpo, e `PUT /api/users/{id}` só altera email e senha.
- IDs na URL são UUID; outro formato responde `422`.

## Como adicionar um erro novo

1. Regra de negócio: crie uma subclasse de `DomainException` em `app/domain/exceptions/`
   com `status_code`, `code` e `default_message`.
2. Erro HTTP em dependência/rota: `raise ApiError(status, "mensagem", code="MEU_CODIGO")`
   (`app/api/errors.py`). Não use `HTTPException` direto: ela cai no `code` padrão do status.
3. Documente o status na rota com `responses=` (`ERROR_404`, `ERROR_409`...) e adicione a linha
   na tabela acima. `tests/integration/api/test_error_handling.py` verifica o formato.
