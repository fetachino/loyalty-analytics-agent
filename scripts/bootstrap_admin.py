"""Create the initial administrator from deployment environment variables."""

import os

from sqlalchemy import select

from loyalty_analytics.auth import hash_password
from loyalty_analytics.database import SessionLocal
from loyalty_analytics.models import User


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    full_name = os.environ.get("ADMIN_FULL_NAME", "Loyalty Administrator").strip()
    if not email:
        raise SystemExit("ADMIN_EMAIL is required")
    if len(password) < 12:
        raise SystemExit("ADMIN_PASSWORD must contain at least 12 characters")

    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=full_name, password_hash="", is_admin=True)
            session.add(user)
        user.full_name = full_name
        user.password_hash = hash_password(password)
        user.is_active = True
        user.is_admin = True
    print(f"Administrator {email} is ready.")


if __name__ == "__main__":
    main()
