"""Authentication and user administration."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import RoleCode
from app.repositories.users import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not verify_password(password, user.password_hash if user else None) or not user.is_active:
            # One generic message: never reveal whether the email exists.
            raise DomainError("Incorrect email or password.", status.HTTP_401_UNAUTHORIZED, "invalid_credentials")
        return user

    def list(self, q: str | None = None, role: str | None = None, active: bool | None = None) -> list[User]:
        return self.users.list(q, role, active)

    def get(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if not user:
            raise DomainError("User not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return user

    def create(self, data: UserCreate) -> User:
        if self.users.get_by_email(data.email):
            raise DomainError("A user with this email already exists.", status.HTTP_409_CONFLICT, "duplicate_email")
        user = User(
            email=data.email.lower(),
            full_name=data.full_name,
            role=self._role(data.role),
            password_hash=hash_password(data.password),
            is_active=True,
        )
        self.users.add(user)
        self.db.commit()
        return user

    def update(self, user_id: int, data: UserUpdate, acting_user: User) -> User:
        user = self.get(user_id)
        losing_admin = user.role.code == RoleCode.ADMIN and (
            (data.role is not None and data.role != RoleCode.ADMIN) or data.is_active is False
        )
        if losing_admin and self.users.count_active_admins() <= 1:
            raise DomainError("At least one active administrator is required.", status.HTTP_409_CONFLICT, "last_admin")
        if user.id == acting_user.id and data.is_active is False:
            raise DomainError("You cannot deactivate your own account.", status.HTTP_409_CONFLICT, "self_deactivate")

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.role is not None:
            user.role = self._role(data.role)
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password:
            user.password_hash = hash_password(data.password)
        self.db.commit()
        return user

    def _role(self, code: RoleCode):
        role = self.users.get_role(code)
        if not role:
            raise DomainError(f"Role '{code}' is not configured.", status.HTTP_400_BAD_REQUEST, "unknown_role")
        return role
