from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user

from app.services import observability


def _mask(email: str) -> str:
    """An unknown e-mail in the logs, without giving it away: a***@finki.ukim.mk."""
    name, _, domain = (email or "").partition("@")
    return (name[:1] + "***@" + domain) if domain else "***"


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=await run_in_threadpool(hash_password, data.password),
        name=data.name,
        role="student",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    observability.set_context(user_id=user.id)
    await observability.activity("register")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user and user.auth_provider != "password":
        raise HTTPException(status_code=401, detail="Use Microsoft sign-in")
    if not user or not await run_in_threadpool(verify_password, data.password, user.password_hash):
        if user:
            observability.set_context(user_id=user.id)
        await observability.activity("login", ok=False, error="Invalid credentials",
                                     email=None if user else _mask(data.email))
        raise HTTPException(status_code=401, detail="Invalid credentials")
    observability.set_context(user_id=user.id)
    await observability.activity("login", method="password")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
