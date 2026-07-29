import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select

from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.auth import create_access_token, decode_access_token, verify_password
from loyalty_analytics.config import get_settings
from loyalty_analytics.models import User
from loyalty_analytics.schemas import LoginRequest, LoginResponse, UserRead

SESSION_COOKIE = "loyalty_session"
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def get_current_user(
    db: DatabaseSession,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    settings = get_settings()
    subject = decode_access_token(session_token or "", settings)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, response: Response, db: DatabaseSession) -> LoginResponse:
    settings = get_settings()
    if settings.auth_secret_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    email = credentials.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    token = create_access_token(str(user.id), settings)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.auth_token_expire_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )
    return LoginResponse(user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="strict")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
