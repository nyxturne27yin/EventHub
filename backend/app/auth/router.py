
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password_reset_email import send_password_reset_email
from app.auth.schemas import (
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
)
from app.auth.utils import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.role import Role
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/swagger-login",
    response_model=TokenResponse,
    include_in_schema=False,
)
async def swagger_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    role_result = await db.execute(
        select(Role).where(Role.name == "student")
    )
    student_role = role_result.scalar_one_or_none()

    if student_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Student role is not configured",
        )

    user = User(
        name=request.full_name,
        email=request.email,
        password_hash=hash_password(request.password),
        role_id=student_role.id,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "full_name": user.name,
        "email": user.email,
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(
        request.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Always return the same response to prevent account enumeration.
    generic_response = {
        "message": (
            "If an eligible account exists, password reset instructions "
            "will be sent to its email address."
        )
    }

    result = await db.execute(
        select(User).where(User.email == str(request.email))
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return generic_response

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    user.password_reset_token_hash = token_hash
    user.password_reset_expires_at = datetime.utcnow() + timedelta(
        minutes=30
    )

    await db.commit()

    background_tasks.add_task(
        send_password_reset_email,
        user.email,
        raw_token,
    )

    return generic_response


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(
        request.token.encode("utf-8")
    ).hexdigest()

    result = await db.execute(
        select(User).where(
            User.password_reset_token_hash == token_hash
        )
    )
    user = result.scalar_one_or_none()

    if (
        user is None
        or user.password_reset_expires_at is None
        or user.password_reset_expires_at <= datetime.utcnow()
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    user.password_hash = hash_password(request.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None

    await db.commit()

    return {"message": "Password has been reset successfully."}


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.name if current_user.role else None,
    }


@router.put("/me")
async def update_me(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.email == request.email,
            User.id != current_user.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    current_user.name = request.name
    current_user.email = request.email

    await db.commit()
    await db.refresh(current_user)

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.name if current_user.role else None,
    }
