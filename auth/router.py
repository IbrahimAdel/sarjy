from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from auth.security import (
    REFRESH_TOKEN_TYPE,
    AuthError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from database import get_session
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

INVALID_CREDENTIALS = "Invalid credentials."
EMAIL_TAKEN = "Email already registered."


def _issue_tokens(user_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: SessionDep,
) -> UserResponse:
    existing = await session.execute(select(User.id).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)

    user = User(
        email=payload.email,
        name=payload.name or payload.email.split("@")[0],
        password=hash_password(payload.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN) from exc

    return UserResponse(id=user.id, email=user.email, name=user.name)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: SessionDep,
) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    return _issue_tokens(user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest) -> TokenResponse:
    try:
        user_id = decode_token(payload.refresh_token, REFRESH_TOKEN_TYPE)
    except AuthError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
        ) from exc
    return _issue_tokens(user_id)
