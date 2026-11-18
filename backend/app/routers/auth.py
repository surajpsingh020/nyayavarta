"""Authentication Router (/api/auth) for Nyayavarta.

Provides endpoints for:
- User Registration with password hashing
- User Login with secure session tokens
- Session Validation (/me)
- User Logout
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status

from app.models.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthResponse,
)
from app.services.auth_db import get_auth_db

logger = logging.getLogger(__name__)

router = APIRouter()


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """Helper to extract token from 'Bearer <token>' header."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization.strip()


def get_current_authenticated_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency that enforces a valid authenticated session."""
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth_db = get_auth_db()
    user = auth_db.validate_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Dependency for endpoints that can work for both logged-in and guest users."""
    token = extract_token_from_header(authorization)
    if not token:
        return None
    auth_db = get_auth_db()
    return auth_db.validate_session(token)


@router.post("/auth/register", response_model=AuthResponse, summary="Register a new user account")
async def register(payload: UserRegisterRequest):
    """Create a new user account and return a session token."""
    auth_db = get_auth_db()
    try:
        result = auth_db.register_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name
        )
        return AuthResponse(
            token=result["token"],
            user=UserResponse(**result["user"])
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error in user registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/auth/login", response_model=AuthResponse, summary="Log in with email and password")
async def login(payload: UserLoginRequest):
    """Authenticate credentials and return a session token."""
    auth_db = get_auth_db()
    try:
        result = auth_db.authenticate_user(
            email=payload.email,
            password=payload.password
        )
        return AuthResponse(
            token=result["token"],
            user=UserResponse(**result["user"])
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error in user login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.get("/auth/me", response_model=UserResponse, summary="Get current logged in user details")
async def get_me(authorization: Optional[str] = Header(None)):
    """Return user data for the current active session."""
    user = get_current_authenticated_user(authorization)
    return UserResponse(**user)


@router.post("/auth/logout", summary="Log out and invalidate session")
async def logout(authorization: Optional[str] = Header(None)):
    """Revoke session token."""
    token = extract_token_from_header(authorization)
    if token:
        auth_db = get_auth_db()
        auth_db.delete_session(token)
    return {"status": "success", "message": "Logged out successfully."}
