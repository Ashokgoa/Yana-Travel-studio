from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models import Role, User
from app.repositories.base import Repository, search_filter


class UserRepository(Repository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User).options(joinedload(User.role)).where(func.lower(User.email) == email.lower())
        )

    def list(self, q: str | None = None, role: str | None = None, active: bool | None = None) -> list[User]:
        stmt = select(User).join(User.role).options(joinedload(User.role)).order_by(User.full_name)
        if q:
            stmt = stmt.where(search_filter(q, User.full_name, User.email))
        if role:
            stmt = stmt.where(Role.code == role)
        if active is not None:
            stmt = stmt.where(User.is_active == active)
        return list(self.db.scalars(stmt))

    def count_active_admins(self) -> int:
        return self.db.scalar(
            select(func.count(User.id)).join(User.role).where(Role.code == "admin", User.is_active.is_(True))
        ) or 0

    def get_role(self, code: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.code == code))
