from fastapi import APIRouter, HTTPException, Depends, Request
from presentation.schemas.user_schema import SignupRequest, LoginRequest, RefreshRequest, UserProfileResponse
from application.auth.register_usecase import register_user
from application.auth.login_usecase import login_user
from presentation.dependencies import get_user_profile, get_db, oauth2_scheme
from infrastructure.security.jwt_service import (
    decode_refresh_token,
    create_access_token,
    decode_access_token,
)
from infrastructure.db.models.user_model import UserModel
from infrastructure.repositories.blacklist_repository import BlacklistRepository
from sqlalchemy.orm import Session
from datetime import datetime
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


# ================== PROFILE ===================
@router.get("/profile")
async def get_profile(
    current_user: UserModel = Depends(get_user_profile),
) -> dict:
    """
    Returns the authenticated user's profile.

    Authentication is handled by get_current_user:
    - Extracts JWT from Authorization header
    - Validates token and expiration
    - Fetches user from database
    - Raises 401 or 404 on failure
    """
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    }


# ==================== LOGOUT ====================
@router.post("/logout")
def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Logout the current user by blacklisting their Access Token.

    Flow:
    1. Client sends POST /auth/logout with Authorization: Bearer <token>
    2. Server decodes the token to determine its expiry
    3. Token is added to the blacklist DB table with its expiry datetime
    4. All future requests using this token will be rejected with 401

    Note: The client MUST delete the token and refresh token from local storage.
    """
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No token provided"
        )

    try:
        blacklist_repo = BlacklistRepository(db)

        # Decode to get the expiry time — we need this so we can clean up
        # expired tokens from the blacklist automatically in the future
        try:
            payload = decode_access_token(token)
            exp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp) if exp else datetime.utcnow()
        except Exception:
            # Even if decode fails (expired), still add it to blacklist for safety
            expires_at = datetime.utcnow()

        # Blacklist the token
        blacklist_repo.blacklist_token(token, expires_at)
        logger.info("Token successfully blacklisted.")

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")