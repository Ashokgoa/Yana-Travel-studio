from typing import Generic, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.database.base import Base

M = TypeVar("M", bound=Base)


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_filter(term: str, *columns):
    pattern = f"%{escape_like(term.strip())}%"
    return or_(*(col.ilike(pattern, escape="\\") for col in columns))


class Repository(Generic[M]):
    model: type[M]

    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: int) -> M | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: M) -> M:
        self.db.add(entity)
        self.db.flush()
        return entity

    def paginate(self, stmt: Select, offset: int, limit: int) -> tuple[list[M], int]:
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        items = list(self.db.scalars(stmt.offset(offset).limit(limit)).unique())
        return items, total
