from passlib.context import CryptContext
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Failed to hash password: {e}")
        raise


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception as e:
        logger.error(f"Failed to verify password: {e}")
        raise
