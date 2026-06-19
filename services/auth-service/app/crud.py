import uuid
from sqlalchemy.orm import Session
from . import security, models, schemas

def get_user_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = security.get_password_hash(user.password)
    
    db_user = models.Usuario(
        id=str(uuid.uuid4()),
        email=user.email,
        senha_hash=hashed_password,
        nome=user.nome,
        cargo=getattr(user, 'cargo', 'aluno')
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not security.verify_password(password, user.senha_hash):
        return None
    return user