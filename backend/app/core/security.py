import hashlib
import hmac
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

# pbkdf2_sha256 has no password length limit (unlike bcrypt's 72-byte cap)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def avatar_url(user_id, version: int | None) -> str | None:
    """Signed link to a profile picture. <img> tags can't send the login token, so the link itself carries a
    signature: only people who were shown the link (people who may see that profile) can load the picture."""
    if not version:
        return None
    return f"/users/{user_id}/avatar?v={version}&s={avatar_signature(user_id, version)}"


def avatar_signature(user_id, version: int) -> str:
    msg = f"avatar:{user_id}:{version}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:24]
