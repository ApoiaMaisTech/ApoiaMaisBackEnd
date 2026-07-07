import hashlib
import hmac
import os

from app.domain.services.password_service import PasswordService

class PasswordServiceImpl(PasswordService):

    SALT_SIZE = 16
    ITERATIONS = 100_000
    HASH_ALGORITHM = "sha256"

    def hash(self, password: str) -> str:
        salt = os.urandom(self.SALT_SIZE).hex()

        derived_key = hashlib.pbkdf2_hmac(
            self.HASH_ALGORITHM,
            password.encode("utf-8"),
            bytes.fromhex(salt),
            self.ITERATIONS,
        )

        return f"{salt}${derived_key.hex()}"

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            salt, stored_hash = password_hash.split("$", 1)
        except ValueError:
            return False

        derived_key = hashlib.pbkdf2_hmac(
            self.HASH_ALGORITHM,
            password.encode("utf-8"),
            bytes.fromhex(salt),
            self.ITERATIONS,
        )

        return hmac.compare_digest(derived_key.hex(), stored_hash)