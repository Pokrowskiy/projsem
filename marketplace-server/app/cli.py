import argparse
from getpass import getpass

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.utils.security import hash_password


def create_admin(email: str) -> None:
    password = getpass("Admin password (8-72 characters): ")
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise SystemExit("Password must contain at least 8 characters and at most 72 UTF-8 bytes")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            raise SystemExit("An account with this email already exists")
        db.add(User(email=email.lower(), password_hash=hash_password(password), role=UserRole.admin))
        db.commit()
    print(f"Administrator {email.lower()} created")


def main() -> None:
    parser = argparse.ArgumentParser(prog="marketplace")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="Create the first administrator account")
    admin.add_argument("email")
    arguments = parser.parse_args()
    if arguments.command == "create-admin":
        create_admin(arguments.email)


if __name__ == "__main__":
    main()