from passlib.context import CryptContext

# O bcrypt será usado aqui para verificar senhas no login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Truncamos antes de verificar para evitar o erro de 72 bytes
    return pwd_context.verify(plain_password[:72], hashed_password)

def get_password_hash(password: str) -> str:
    # Truncamos antes de criar o hash
    return pwd_context.hash(password[:72])