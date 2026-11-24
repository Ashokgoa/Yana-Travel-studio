"""Pricing DTOs (Phase 7).

INTERNAL (planners and admins): `PricingView` with costs, margins and profit.
CUSTOMER: `CustomerPrice` holds selling prices only. It is the only pricing
object the PDF builder receives, so costs can't leak into proposals.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.engines.pricing import BASES, CATEGORIES

Category = Literal[CATEGORIES]  # type: ignore[valid-type]
Basis = Literal[BASES]  # type: ignore[valid-type]
Pct = Decimal
CATEGORY_LABELS = {"hotel": "Hotels", "transport": "Transport", "transfer": "Transfers", "sightseeing": "Sightseeing",
                   "guide": "Guides", "meal": "Meals", "other": "Other"}
BASIS_LABELS = {"per_person": "per person", "per_room": "per room per night", "per_day": "per day", "per_vehicle": "per vehicle",
                "per_km": "per km", "group": "per group"}


def _margins(value: dict[str, Decimal]) -> dict[str, Decimal]:
    unknown = set(value) - set(CATEGORIES)
    if unknown:
        raise ValueError(f"Unknown categories: {', '.join(sorted(unknown))}")
    for k, v in value.items():
        if not Decimal(0) <= Decimal(v) <= Decimal(300):
            raise ValueError(f"Margin for {k} must be between 0 and 300%")
    return value


class PricingDefaults(BaseModel):
    """Administrator defaults, copied into each new pricing sheet."""

    margins: dict[str, Decimal] = Field(default_factory=lambda: {c: Decimal(15) for c in CATEGORIES})
    rounding: Decimal = Field(default=Decimal(1), ge=0, le=1000)
    child_bed_pct: Decimal = Field(default=Decimal(100), ge=0, le=100)
    display_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    exchange_rate: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    margins_reviewed: bool = False

    @field_validator("margins")
    @classmethod
    def _check_margins(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        return _margins(v)


class PricingSettingsUpdate(BaseModel):
    margins: dict[str, Decimal] | None = None
    discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    adjustment_per_person: Decimal | None = Field(default=None, ge=-100_000, le=100_000)
    rounding: Decimal | None = Field(default=None, ge=0, le=1000)
    child_bed_pct: Decimal | None = Field(default=None, ge=0, le=100)
    adults: int | None = Field(default=None, ge=0, le=500)
    children_with_bed: int | None = Field(default=None, ge=0, le=500)
    children_without_bed: int | None = Field(default=None, ge=0, le=500)
    singles: int | None = Field(default=None, ge=0, le=500)
    display_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    exchange_rate: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    pdf_currency: Literal["base", "display", "both"] | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("margins")
    @classmethod
    def _check_margins(cls, v: dict[str, Decimal] | None) -> dict[str, Decimal] | None:
        return v if v is None else _margins(v)


class LineOverride(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    unit_cost: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    clear_unit_cost: bool = False  # explicitly set "no price" (unknown)
    quantity: Decimal | None = Field(default=None, ge=0, le=100_000)
    included: bool | None = None


class StayRateOverride(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    double_rate: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    single_rate: Decimal | None = Field(default=None, ge=0, le=1_000_000)


class ManualLineIn(BaseModel):
    category: Category
    basis: Basis
    description: str = Field(min_length=1, max_length=300)
    unit_cost: Decimal | None = Field(default=None, ge=0, le=10_000_000)
    quantity: Decimal = Field(default=Decimal(1), ge=0, le=100_000)
    is_estimate: bool = True


QuoteStatus = Literal["estimate", "quoted", "confirmed"]


class QuoteIn(BaseModel):
    """A supplier's price for one cost line. Amount in the supplier's currency; converted with fx_rate."""

    key: str = Field(min_length=1, max_length=200)
    supplier_id: int | None = None
    supplier_rate_id: int | None = None
    amount: Decimal = Field(ge=0, le=10_000_000)
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    fx_rate: Decimal | None = Field(default=None, gt=0, le=100_000)  # 1 unit of `currency` = fx_rate base currency
    status: QuoteStatus = "quoted"
    reference: str | None = Field(default=None, max_length=200)
    save_as_rate: bool = False  # also add this price to the supplier's rate card
    service: str | None = Field(default=None, max_length=200)  # rate card name when save_as_rate


class SupplierRateIn(BaseModel):
    service: str = Field(min_length=1, max_length=200)
    category: Category
    basis: Basis
    unit_cost: Decimal = Field(ge=0, le=10_000_000)
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    valid_from: date | None = None
    valid_to: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class SupplierRateOut(SupplierRateIn):
    id: int
    supplier_id: int
    supplier_name: str | None = None
    valid_on_trip: bool | None = None


class LineOut(BaseModel):
    key: str
    manual_id: int | None = None
    category: str
    basis: str
    description: str
    unit_cost: str | None
    quantity: str
    total: str | None  # group total
    is_estimate: bool
    included: bool
    is_overridden: bool = False
    auto_unit_cost: str | None = None
    status: str = "estimate"  # estimate / quoted / confirmed
    supplier_id: int | None = None
    supplier_name: str | None = None
    quote: dict | None = None  # {amount, currency, fx_rate, reference, supplier_rate_id}


class StayRateOut(BaseModel):
    key: str
    label: str
    nights: int
    double_rate: str | None
    single_rate: str | None
    single_is_estimate: bool
    is_overridden: bool


class CategoryOut(BaseModel):
    category: str
    label: str
    cost: str
    margin_pct: str
    per_person_cost: str
    per_person_selling: str


class Prices(BaseModel):
    currency: str
    adult_twin: str | None
    single_supplement: str | None
    child_with_bed: str | None
    child_without_bed: str | None


class CustomerPrice(BaseModel):
    """Selling prices only (safe for proposals)."""

    base: Prices
    display: Prices | None = None
    show: Literal["base", "display", "both"] = "base"
    has_children: bool = False
    is_incomplete: bool = False


class PricingView(BaseModel):
    """INTERNAL: costs, margins and profit. Never sent to customer views."""

    version_number: int
    version_label: str
    currency: str
    margins: dict[str, str]
    discount_pct: str
    adjustment_per_person: str
    rounding: str
    child_bed_pct: str
    adults: int
    children_with_bed: int
    children_without_bed: int
    singles: int
    travellers_from_enquiry: dict[str, int]
    display_currency: str | None
    exchange_rate: str | None
    pdf_currency: str
    notes: str | None
    lines: list[LineOut]
    stays: list[StayRateOut]
    categories: list[CategoryOut]
    prices: Prices
    display_prices: Prices | None
    adult_twin_cost: str
    total_cost: str
    revenue: str
    profit: str
    margin_on_revenue_pct: str | None
    budget_per_person: str | None
    warnings: list[str]
    margins_reviewed: bool
    trip_start: date
    fx_rates: dict[str, str]
    quote_progress: dict[str, int]  # confirmed / quoted / estimate / total (included lines)
