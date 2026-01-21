from fastapi import APIRouter, HTTPException
from presentation.schemas.user_schema import SignupRequest, LoginRequest, RefreshRequest
from application.auth.register_usecase import register_user
from application.auth.login_usecase import login_user
from infrastructure.security.jwt_service import (
    decode_refresh_token,
    create_access_token,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== SIGNUP ====================
@router.post("/signup")
def signup(request: SignupRequest):
    """
    Register a new user.
    """
    try:
        logger.info(f"Signup attempt for email: {request.email}")
        result = register_user(
            name=request.name,
            email=request.email,
            password=request.password,
            role=request.role,
        )
        logger.info(f"Signup successful for email: {request.email}")
        return result
    except ValueError as ve:
        logger.warning(f"Signup validation error for {request.email}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(
            f"Unexpected error during signup for {request.email}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== LOGIN ====================
@router.post("/login")
def login(request: LoginRequest):
    """
    Authenticate a user and return access & refresh tokens.
    """
    try:
        logger.info(f"Login attempt for email: {request.email}")
        result = login_user(email=request.email, password=request.password)
        logger.info(f"Login successful for email: {request.email}")
        return result
    except ValueError as ve:
        logger.warning(f"Login failed for {request.email}: {ve}")
        raise HTTPException(status_code=401, detail=str(ve))
    except Exception as e:
        logger.error(
            f"Unexpected error during login for {request.email}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== TOKEN REFRESH ====================
@router.post("/refresh")
def refresh(request: RefreshRequest):
    """
    Refresh access token using a valid refresh token.
    """
    try:
        logger.info("Token refresh attempt")
        payload = decode_refresh_token(request.refresh_token)
        new_access_token = create_access_token(
            {"user_id": payload["user_id"], "role": payload["role"]}
        )
        logger.info(f"Token refresh successful for user_id: {payload.get('user_id')}")
        return {"access_token": new_access_token, "token_type": "bearer"}
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
