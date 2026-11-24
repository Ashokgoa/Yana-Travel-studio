"""Pricing sheets (Phase 7): the commercial layer of an itinerary version.

Automatic cost lines are derived from the version's content every time the
sheet is read (so edits to the itinerary flow through); the sheet stores only
the planner's decisions: margins per category, discount, adjustment, rounding,
traveller split, overrides of automatic lines (by stable key), room-rate
overrides, extra manual lines and the optional display currency.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin


class PricingSheet(IdMixin, TimestampMixin, Base):
    __tablename__ = "pricing_sheets"

    version_id: Mapped[int] = mapped_column(ForeignKey("itinerary_versions.id", ondelete="CASCADE"), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    margins: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {category: pct}
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    adjustment_per_person: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    rounding: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    child_bed_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100, nullable=False)
    # Traveller split; NULL = taken from the enquiry requirements.
    adults: Mapped[int | None] = mapped_column(Integer)
    children_with_bed: Mapped[int | None] = mapped_column(Integer)
    children_without_bed: Mapped[int | None] = mapped_column(Integer)
    singles: Mapped[int | None] = mapped_column(Integer)
    overrides: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {line key: {unit_cost, quantity, included}}
    stay_overrides: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {stay key: {double_rate, single_rate}}
    display_currency: Mapped[str | None] = mapped_column(String(3))
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))  # 1 base = rate display
    pdf_currency: Mapped[str] = mapped_column(String(10), default="base", nullable=False)  # base / display / both
    notes: Mapped[str | None] = mapped_column(Text)
    # Exchange rates used for supplier quotes in other currencies: {"CHF": "1.06"} (1 CHF = 1.06 base).
    fx_rates: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    lines: Mapped[list["PricingLine"]] = relationship(back_populates="sheet", cascade="all, delete-orphan", order_by="PricingLine.sort_order")


class PricingLine(IdMixin, TimestampMixin, Base):
    """Extra cost line added by the planner (guides, tolls, parking, extras)."""

    __tablename__ = "pricing_lines"

    sheet_id: Mapped[int] = mapped_column(ForeignKey("pricing_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    basis: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Supplier quote (Phase 8c): what the supplier quoted, in their currency, and how sure it is.
    quote: Mapped[dict | None] = mapped_column(JSON)

    sheet: Mapped[PricingSheet] = relationship(back_populates="lines")


class SupplierRate(IdMixin, TimestampMixin, Base):
    """A supplier's price for one service (rate card), optionally for a season (valid from / to)."""

    __tablename__ = "supplier_rates"

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    basis: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
