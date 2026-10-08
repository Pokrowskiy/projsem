from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


def validate_bcrypt_password_size(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return password


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.buyer
    full_name: str | None = Field(default=None, max_length=120)

    _password_size = field_validator("password")(validate_bcrypt_password_size)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    _password_size = field_validator("password")(validate_bcrypt_password_size)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    full_name: str | None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
