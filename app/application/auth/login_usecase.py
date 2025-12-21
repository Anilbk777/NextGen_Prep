from infrastructure.db.session import SessionLocal
from infrastructure.db.models.user_model import UserModel
from infrastructure.security.password_hash import verify_password
from infrastructure.security.jwt_service import create_access_token, create_refresh_token
import logging

logger = logging.getLogger(__name__)


def login_user(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user:
            logger.warning(f"Login failed, user not found: {email}")
            raise ValueError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            logger.warning(f"Login failed, wrong password: {email}")
            raise ValueError("Invalid credentials")

        access_token = create_access_token({"user_id": user.id, "role": user.role})
        refresh_token = create_refresh_token({"user_id": user.id, "role": user.role})
        
        logger.info(f"User logged in successfully: {email}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user.role
        }
    except ValueError:
        # Re-raise known value errors (credentials)
        raise
    except Exception as e:
        logger.error(f"Unexpected login error for {email}: {e}", exc_info=True)
        raise
    finally:
        db.close()
