from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from loyalty_analytics.config import Settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(subject: str, settings: Settings) -> str:
    if settings.auth_secret_key is None:
        raise RuntimeError("AUTH_SECRET_KEY is not configured")
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.auth_secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str, settings: Settings) -> str | None:
    if settings.auth_secret_key is None:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key.get_secret_value(),
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
