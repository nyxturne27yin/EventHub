import asyncio
import getpass
import re

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.utils import hash_password
from app.database.database import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User


def valid_password(password: str) -> bool:
    return (
        8 <= len(password) <= 128
        and re.search(r"[A-Za-z]", password) is not None
        and re.search(r"\d", password) is not None
        and re.search(r"[@$!%*?&]", password) is not None
    )


async def create_admin() -> int:
    name = input("Administrator full name: ").strip()
    if not name or len(name) > 100:
        print("Invalid name: enter 1 to 100 characters.")
        return 1

    try:
        email = str(
            TypeAdapter(EmailStr).validate_python(
                input("Administrator email: ").strip().lower()
            )
        )
    except ValidationError:
        print("Invalid email address.")
        return 1

    password = getpass.getpass("New administrator password: ")
    if not valid_password(password):
        print(
            "Password must be 8-128 characters and contain "
            "a letter, a number, and one of @$!%*?&."
        )
        return 1

    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.")
        return 1

    async with AsyncSessionLocal() as db:
        role_result = await db.execute(
            select(Role).where(Role.name == "administrator")
        )
        admin_role = role_result.scalar_one_or_none()

        if admin_role is None:
            print("Administrator role is missing. Apply the approved migrations first.")
            return 1

        user_result = await db.execute(
            select(User).where(User.email == email)
        )
        if user_result.scalar_one_or_none() is not None:
            print("An account with this email already exists.")
            return 1

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(admin)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            print("Account could not be created; check for a duplicate email.")
            return 1

    print("Administrator account created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(create_admin()))
