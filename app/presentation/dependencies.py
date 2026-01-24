from infrastructure.db.session import SessionLocal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from infrastructure.security.jwt_service import decode_access_token
import logging

logger = logging.getLogger(__name__)

# Set auto_error=False to allow our manual toggle inside get_current_user to work
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    To switch to testing mode:
    1. Uncomment the 'TESTING MODE' block
    2. Comment out the 'PRODUCTION MODE' block
    """

    # --- [ BLOCK 1: TESTING MODE ] ---
    if not token:
        logger.info("Auth bypass triggered: Using Mock Test User (USER)")
        return {"user_id": 1, "role": "ADMIN"}
    # ----------------------------------

    # --- [ BLOCK 2: PRODUCTION MODE ] ---
    # if not token:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Not authenticated",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    # ------------------------------------

    try:
        payload = decode_access_token(token)
        logger.debug(f"Validated token for user_id: {payload.get('user_id')}")
        return payload
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def admin_required(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "ADMIN":
        logger.warning(
            f"Access denied for non-admin user_id: {current_user.get('user_id')}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required",
        )
    logger.info(f"Admin access granted for user_id: {current_user.get('user_id')}")
    return current_user
