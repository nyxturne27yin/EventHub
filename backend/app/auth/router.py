from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RegisterRequest, UserResponse
from app.auth.utils import hash_password
from app.database.database import get_db
from app.models.role import Role
from app.models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get("/test")
async def auth_test():
    return {"message": "Auth router working"}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    result = await db.execute(
        select(Role).where(Role.name == "student")
    )

    role = result.scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Student role not found",
        )

    hashed_password = hash_password(data.password)

    new_user = User(
        name=data.name,
        email=data.email,
        password_hash=hashed_password,
        role_id=role.id,
    )

    db.add(new_user)

    await db.commit()
    await db.refresh(new_user)

    return new_user
