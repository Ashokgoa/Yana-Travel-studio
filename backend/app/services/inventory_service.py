"""Generic inventory CRUD driven by a declarative `Resource` description.

Each inventory type (countries, cities, hotels, ...) declares its model,
schemas, search columns, filters and foreign-key checks once; this service
then provides consistent list/get/create/update/activate behaviour.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import status
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.repositories.base import search_filter
from app.schemas.common import Page, PageParams

FilterFn = Callable[[Select, Any], Select]


@dataclass
class Filter:
    parse: Callable[[str], Any]
    apply: FilterFn


def _bool(v: str) -> bool:
    if v.lower() in ("true", "1", "yes"):
        return True
    if v.lower() in ("false", "0", "no"):
        return False
    raise ValueError(v)


def eq(column, parse: Callable[[str], Any] = int) -> Filter:
    return Filter(parse, lambda stmt, v: stmt.where(column == v))


def is_true(column) -> Filter:
    """`?jain=true` → only rows where the flag is verified True (unknown is excluded)."""
    return Filter(_bool, lambda stmt, v: stmt.where(column.is_(True)) if v else stmt)


@dataclass
class Resource:
    name: str
    label: str
    model: type
    schema_in: type[BaseModel]
    schema_out: type[BaseModel]
    search_columns: list = field(default_factory=list)
    filters: dict[str, Filter] = field(default_factory=dict)
    order_by: list = field(default_factory=list)
    load_options: list = field(default_factory=list)
    joins: list = field(default_factory=list)
    # field name on the input schema -> (model, human label) that must exist
    references: dict[str, tuple[type, str]] = field(default_factory=dict)
    # media entity type for images ("hotel", ...); None = no images
    entity_type: str | None = None
    # hooks
    to_columns: Callable[[Session, BaseModel], dict] | None = None
    enrich: Callable[[Session, list], dict[int, dict]] | None = None
    duplicate_message: str = "A record with these details already exists."


class InventoryService:
    def __init__(self, db: Session, resource: Resource):
        self.db = db
        self.r = resource

    # -------------------------------------------------------------- queries
    def _base(self) -> Select:
        stmt = select(self.r.model)
        for j in self.r.joins:
            stmt = stmt.join(j)
        return stmt.options(*self.r.load_options)

    def list(self, q: str | None, active: bool | None, raw_filters: dict[str, str], page: PageParams) -> Page:
        stmt = self._base().order_by(*self.r.order_by)
        if q and self.r.search_columns:
            stmt = stmt.where(search_filter(q, *self.r.search_columns))
        if active is not None:
            stmt = stmt.where(self.r.model.is_active.is_(active))
        for key, raw in raw_filters.items():
            flt = self.r.filters.get(key)
            if flt is None or raw in ("", None):
                continue
            try:
                value = flt.parse(raw)
            except (ValueError, TypeError):
                raise DomainError(f"Invalid value for filter '{key}'.", status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_filter")
            stmt = flt.apply(stmt, value)

        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        rows = list(self.db.scalars(stmt.offset(page.offset).limit(page.page_size)).unique())
        return Page(items=self._out_many(rows), total=total, page=page.page, page_size=page.page_size)

    def get(self, entity_id: int) -> BaseModel:
        return self._out_many([self._get(entity_id)])[0]

    def _get(self, entity_id: int):
        obj = self.db.scalar(self._base().where(self.r.model.id == entity_id))
        if obj is None:
            raise DomainError(f"{self.r.label} not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return obj

    # -------------------------------------------------------------- writes
    def create(self, data: BaseModel) -> BaseModel:
        self._check_references(data)
        obj = self.r.model(**self._columns(data))
        self.db.add(obj)
        self._commit()
        return self.get(obj.id)

    def update(self, entity_id: int, data: BaseModel) -> BaseModel:
        obj = self._get(entity_id)
        self._check_references(data)
        for key, value in self._columns(data).items():
            setattr(obj, key, value)
        self._commit()
        self.db.expire_all()
        return self.get(entity_id)

    def set_active(self, entity_id: int, active: bool) -> BaseModel:
        obj = self._get(entity_id)
        obj.is_active = active
        self._commit()
        return self.get(entity_id)

    # -------------------------------------------------------------- helpers
    def _columns(self, data: BaseModel) -> dict:
        if self.r.to_columns:
            return self.r.to_columns(self.db, data)
        return data.model_dump()

    def _check_references(self, data: BaseModel) -> None:
        for field_name, (model, label) in self.r.references.items():
            ref_id = getattr(data, field_name, None)
            if ref_id is not None and self.db.get(model, ref_id) is None:
                raise DomainError(f"Selected {label} does not exist.", status.HTTP_400_BAD_REQUEST, "invalid_reference")

    def _commit(self) -> None:
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise DomainError(self.r.duplicate_message, status.HTTP_409_CONFLICT, "duplicate")

    def _out_many(self, rows: list) -> list[BaseModel]:
        extra = self.r.enrich(self.db, rows) if (self.r.enrich and rows) else {}
        images = self._primary_images(rows) if self.r.entity_type else {}
        out = []
        for row in rows:
            item = self.r.schema_out.model_validate(row)
            updates = {**extra.get(row.id, {})}
            if row.id in images:
                updates["primary_image_url"] = images[row.id]
            out.append(item.model_copy(update=updates) if updates else item)
        return out

    def _primary_images(self, rows: list) -> dict[int, str]:
        from app.services.media_service import primary_image_urls  # local import: avoid cycle

        return primary_image_urls(self.db, self.r.entity_type, [r.id for r in rows])
