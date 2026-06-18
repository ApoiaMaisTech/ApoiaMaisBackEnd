from sqlalchemy.orm import Session
from . import security
from . import models, schemas
def authenticate_user(db: Session, email: str, password: str):

    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not user:
        return None
    if not security.verify_password(password, user.senha_hash):
        return None
    return user