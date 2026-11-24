"""Supplier rate cards (Phase 8c): each supplier's prices per service, optionally per season."""

from __future__ import annotations

from datetime import date

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Supplier, SupplierRate
from app.schemas.pricing import SupplierRateIn, SupplierRateOut


def _check_dates(data: SupplierRateIn) -> None:
    if data.valid_from and data.valid_to and data.valid_to < data.valid_from:
        raise DomainError("“Valid to” must be on or after “Valid from”.", status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_dates")


def out(r: SupplierRate, supplier_name: str | None = None, on: date | None = None) -> SupplierRateOut:
    valid = None
    if on:
        valid = (r.valid_from is None or r.valid_from <= on) and (r.valid_to is None or on <= r.valid_to)
    return SupplierRateOut(id=r.id, supplier_id=r.supplier_id, supplier_name=supplier_name, service=r.service, category=r.category, basis=r.basis,
                           unit_cost=r.unit_cost, currency=r.currency, valid_from=r.valid_from, valid_to=r.valid_to, notes=r.notes,
                           is_active=r.is_active, valid_on_trip=valid)


class SupplierRateService:
    def __init__(self, db: Session):
        self.db = db

    def _supplier(self, supplier_id: int) -> Supplier:
        s = self.db.get(Supplier, supplier_id)
        if s is None:
            raise DomainError("Supplier not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return s

    def _rate(self, rate_id: int) -> SupplierRate:
        r = self.db.get(SupplierRate, rate_id)
        if r is None:
            raise DomainError("Rate not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return r

    def for_supplier(self, supplier_id: int) -> list[SupplierRateOut]:
        s = self._supplier(supplier_id)
        rows = self.db.scalars(select(SupplierRate).where(SupplierRate.supplier_id == supplier_id)
                               .order_by(SupplierRate.category, SupplierRate.service, SupplierRate.valid_from))
        return [out(r, s.name) for r in rows]

    def search(self, category: str | None, on: date | None, supplier_id: int | None = None) -> list[SupplierRateOut]:
        stmt = (select(SupplierRate, Supplier.name).join(Supplier, Supplier.id == SupplierRate.supplier_id)
                .where(SupplierRate.is_active.is_(True), Supplier.is_active.is_(True)))
        if category:
            stmt = stmt.where(SupplierRate.category == category)
        if supplier_id:
            stmt = stmt.where(SupplierRate.supplier_id == supplier_id)
        rows = [out(r, name, on) for r, name in self.db.execute(stmt.order_by(Supplier.name, SupplierRate.service, SupplierRate.valid_from))]
        return sorted(rows, key=lambda x: (x.valid_on_trip is False, x.supplier_name or "", x.service))

    def create(self, supplier_id: int, data: SupplierRateIn) -> SupplierRateOut:
        s = self._supplier(supplier_id)
        _check_dates(data)
        r = SupplierRate(supplier_id=supplier_id, **data.model_dump())
        self.db.add(r)
        self.db.commit()
        return out(r, s.name)

    def update(self, rate_id: int, data: SupplierRateIn) -> SupplierRateOut:
        r = self._rate(rate_id)
        _check_dates(data)
        for k, v in data.model_dump().items():
            setattr(r, k, v)
        self.db.commit()
        return out(r, self._supplier(r.supplier_id).name)

    def delete(self, rate_id: int) -> None:
        self.db.delete(self._rate(rate_id))
        self.db.commit()
