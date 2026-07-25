"""Create or update an administrative dashboard user."""

import argparse
import getpass

from sqlalchemy import select

from loyalty_analytics.auth import hash_password
from loyalty_analytics.database import SessionLocal
from loyalty_analytics.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Loyalty Administrator")
    args = parser.parse_args()
    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    email = args.email.strip().lower()
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=args.name, password_hash="", is_admin=True)
            session.add(user)
        user.full_name = args.name
        user.password_hash = hash_password(password)
        user.is_active = True
        user.is_admin = True
    print(f"Administrator {email} is ready.")


if __name__ == "__main__":
    main()
