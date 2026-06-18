from sqlalchemy.orm import Session
from . import models, schemas
import uuid

def get_user(db: Session, user_id: str):
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    # Nota: No user-service, assumimos que a senha já chega hashada do auth-service
    db_user = models.Usuario(
        id=str(uuid.uuid4()),
        email=user.email,
        nome=user.nome,
        senha_hash=user.password, # Espera-se a senha hashada aqui
        cargo="professor"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Usuario).offset(skip).limit(limit).all()