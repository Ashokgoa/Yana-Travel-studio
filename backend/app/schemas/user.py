from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.security import MIN_PASSWORD_LENGTH
from app.models.enums import RoleCode
from app.schemas.common import ORMModel, RequiredStr


class RoleOut(ORMModel):
    id: int
    code: str
    name: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    role: RoleOut
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: RequiredStr = Field(max_length=200)
    role: RoleCode
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class UserUpdate(BaseModel):
    full_name: RequiredStr | None = Field(default=None, max_length=200)
    role: RoleCode | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=MIN_PASSWORD_LENGTH, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
