from infrastructure.db.session import SessionLocal
from infrastructure.db.models.user_model import UserModel
from infrastructure.security.password_hash import hash_password, verify_password
from infrastructure.security.jwt_service import create_access_token
import logging

logger = logging.getLogger(__name__)


def register_user(name: str, email: str, password: str, role: str = "USER") -> dict :
    db = SessionLocal()
    try:
        logger.info(f"Attempting to register user: {email}")
        existing_user = db.query(UserModel).filter(UserModel.email == email).first()
        if existing_user:
            logger.warning(f"Registration failed, user already exists: {email}")
            raise ValueError("User already exists")

        hashed_password = hash_password(password)
        user = UserModel(name=name, email=email, password_hash=hashed_password, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User registered successfully: {email}")
        return {"id": user.id,"name":name, "email": user.email, "role": user.role}
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to register user {email}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
