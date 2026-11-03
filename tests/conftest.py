import os

# Antes de qualquer import do app: sem pool de conexões nos testes. O TestClient roda
# cada requisição num event loop próprio, e conexão de pool fica presa ao loop de origem.
os.environ.setdefault("DB_POOL_SIZE", "0")
