import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, computed_field

from app.core.security import avatar_url as _avatar_url


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    auth_provider: str = "password"
    created_at: datetime
    avatar_version: Optional[int] = None

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def avatar_url(self) -> Optional[str]:
        return _avatar_url(self.id, self.avatar_version)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
