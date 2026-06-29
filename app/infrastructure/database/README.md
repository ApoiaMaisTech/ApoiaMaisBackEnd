# 🗄️ app/infrastructure/database/

O diretório `database/` é responsável por toda a configuração de **persistência de dados** da aplicação: conexão com o banco de dados, gerenciamento de sessões, definição de modelos ORM e implementação dos repositórios.

---

## 🗂️ Estrutura

```text
database/
├── connection.py         # Engine e configuração da conexão com o banco
├── session.py            # Gerenciamento de sessões SQLAlchemy
├── base.py               # Classe base declarativa dos modelos ORM
├── models/               # Modelos ORM mapeados para tabelas do banco
│   ├── user_model.py
│   └── report_model.py
└── repositories/         # Implementação do padrão Repository
    ├── user_repository.py
    └── report_repository.py
```

---

## 📄 Arquivos Principais

### `connection.py`
Cria o **engine** do SQLAlchemy a partir da `DATABASE_URL` definida nas configurações:

```python
from sqlalchemy import create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
```

---

### `session.py`
Define o **SessionLocal** e a dependência `get_db` utilizada via `Depends` nas rotas:

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### `base.py`
Classe base declarativa compartilhada por todos os modelos ORM:

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

---

## 🔧 Banco de Dados Suportado

| Banco de Dados | Driver             | Status      |
|----------------|--------------------|-------------|
| MySQL          | `pymysql`          | ✅ Produção  |
| SQLite         | nativo             | ✅ Testes    |
| PostgreSQL     | `psycopg2`         | 🔄 Opcional  |

---

## 📐 Padrão Repository

Todos os repositórios seguem o padrão **Repository Pattern**, encapsulando as operações de banco de dados:

```python
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, user_id: int) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def save(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

---

## 🚀 Migrations

As migrações de banco de dados são gerenciadas pelo **Alembic**:

```bash
# Gerar nova migration
alembic revision --autogenerate -m "descricao"

# Aplicar migrations
alembic upgrade head

# Reverter última migration
alembic downgrade -1
```