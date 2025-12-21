from datetime import datetime, timedelta
import jwt
import logging

import os

SECRET_KEY = os.getenv("SECRET_KEY", "secret123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

logger = logging.getLogger(__name__)


def create_access_token(data: dict):
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Failed to create JWT token: {e}")
        raise


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise
    except jwt.PyJWTError as e:
        logger.error(f"Invalid token: {e}")
        raise


def create_refresh_token(data: dict):
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise jwt.PyJWTError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Refresh token expired")
        raise
    except jwt.PyJWTError as e:
        logger.error(f"Invalid refresh token: {e}")
        raise
