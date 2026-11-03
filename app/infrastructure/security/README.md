# app/infrastructure/security/

Implementações de segurança usadas pela autenticação.

## `password.py` — PasswordServiceImpl

Implementa `PasswordService` com **PBKDF2-HMAC-SHA256** da biblioteca padrão (`hashlib`).

| Parâmetro  | Valor |
|------------|-------|
| Algoritmo  | `sha256` |
| Iterações  | 100.000 |
| Salt       | 16 bytes aleatórios (`os.urandom`) |

Formato armazenado em `user.password_hash`:

```text
<salt em hex>$<hash derivado em hex>
```

A verificação usa `hmac.compare_digest`, que compara em tempo constante. Um hash fora do formato retorna `False`.

O cálculo é síncrono e roda dentro das rotas assíncronas; durante o hash, o event loop do worker fica bloqueado.

## `jwt.py` — JwtServiceImpl

Gera e valida tokens JWT com **PyJWT**.

Construtor:

```python
JwtServiceImpl(secret_key: str | None = None, algorithm: str = "HS256", expiration_minutes: int = 30)
```

`secret_key` é obrigatório (vem de `settings.JWT_SECRET_KEY`); não há valor padrão.

Claims do token:

| Claim        | Conteúdo |
|--------------|----------|
| `user_id`    | UUID do usuário (string) |
| `role`       | Valor da role (`student`, `teacher`, ...) |
| `iat`        | Emissão |
| `exp`        | Expiração, calculada a partir de `expiration_minutes` |

O e-mail **não** vai no token (LGPD: o payload de um JWT é legível por quem o tiver). A cada
requisição `get_current_user` confere o usuário no banco, então conta removida perde o acesso
na hora. Não há refresh token nem claims `iss`, `aud` ou `jti`.

### Onde é instanciado

| Local | Uso | Configuração |
|-------|-----|--------------|
| `app/api/dependencies/services.py` | Geração do token no login | `settings.JWT_SECRET_KEY` e `settings.JWT_ALGORITHM`; expiração padrão de 30 minutos |
| `app/api/dependencies/auth.py` | Validação do token nas rotas protegidas | Sem argumentos: chave via `os.getenv`, algoritmo `HS256` |

As duas instâncias precisam usar a mesma chave e o mesmo algoritmo. `JWT_EXPIRE_MINUTES` ainda não é repassado ao serviço.
