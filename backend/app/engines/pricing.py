"""Pricing engine (Phase 7): pure functions over plain dataclasses.

Price presentation (YANA decision, 2026-11-24): per adult in a twin/double
room, plus single supplement and child prices (with / without bed). Margins
are a mark-up percentage per service category, added on top of cost.

How a per-person price is built
-------------------------------
* shared costs (basis per_day / per_vehicle / per_km / group, e.g. coach,
  guide, tolls) are divided by all paying travellers (adults + children);
* per-person costs (tickets, meals, train fares) count once per person;
* hotel: half a double room per night (twin share) for an adult; the single
  supplement is the single-room rate minus that twin share; a child without
  bed has no hotel share; a child with bed pays `child_bed_pct` % of it.

Each component gets its own category's margin. Discount %, an adjustment per
person and rounding (up to the nearest unit) are applied to the final prices.
The group revenue (prices x travellers) is compared with the ACTUAL cost of
all lines (the real room plan) to show profit and the effective margin.

All amounts are Decimal. Unknown costs (None) are reported, never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

CATEGORIES = ("hotel", "transport", "transfer", "sightseeing", "guide", "meal", "other")
BASES = ("per_person", "per_room", "per_day", "per_vehicle", "per_km", "group")
SHARED_BASES = {"per_day", "per_vehicle", "per_km", "group"}
ZERO = Decimal(0)
CENT = Decimal("0.01")


@dataclass
class CostLine:
    key: str
    category: str
    basis: str
    description: str
    unit_cost: Decimal | None
    quantity: Decimal
    is_estimate: bool = True
    included: bool = True

    @property
    def total(self) -> Decimal | None:
        """Total for the group. per_person lines multiply by travellers in `price()`."""
        return None if self.unit_cost is None else self.unit_cost * self.quantity


@dataclass
class StayRate:
    key: str
    label: str
    nights: int
    double_rate: Decimal | None  # per room per night
    single_rate: Decimal | None  # per room per night
    single_is_estimate: bool = False  # single = double rate (no single room type known)


@dataclass
class PricingInput:
    adults: int
    children_with_bed: int
    children_without_bed: int
    singles: int  # adults in single rooms (pay the supplement)
    margins: dict[str, Decimal]
    discount_pct: Decimal = ZERO
    adjustment_per_person: Decimal = ZERO
    rounding: Decimal = Decimal(1)
    child_bed_pct: Decimal = Decimal(100)
    lines: list[CostLine] = field(default_factory=list)
    stays: list[StayRate] = field(default_factory=list)

    @property
    def children(self) -> int:
        return self.children_with_bed + self.children_without_bed

    @property
    def travellers(self) -> int:
        return self.adults + self.children


@dataclass
class CategoryResult:
    category: str
    cost: Decimal  # actual group cost of the lines
    margin_pct: Decimal
    per_person_cost: Decimal  # this category's part of the adult twin price, before margin
    per_person_selling: Decimal


@dataclass
class PricingResult:
    adult_twin: Decimal | None
    single_supplement: Decimal | None
    child_with_bed: Decimal | None
    child_without_bed: Decimal | None
    adult_twin_cost: Decimal
    categories: list[CategoryResult]
    total_cost: Decimal
    revenue: Decimal
    profit: Decimal
    margin_on_revenue_pct: Decimal | None
    unpriced: list[str]
    warnings: list[str]


def _q(v: Decimal) -> Decimal:
    return v.quantize(CENT, ROUND_HALF_UP)


def round_up(value: Decimal, unit: Decimal) -> Decimal:
    """Round up to the nearest `unit` (1, 5, 10, 50 ...). unit <= 0 means 2 decimals."""
    value = _q(value)  # cents first, so 499.9999... does not become 500 + 1
    if unit <= 0:
        return value
    return (value / unit).to_integral_value(ROUND_CEILING) * unit


def line_group_total(line: CostLine, travellers: int) -> Decimal | None:
    if line.unit_cost is None:
        return None
    return line.unit_cost * line.quantity * (travellers if line.basis == "per_person" else 1)


def price(inp: PricingInput) -> PricingResult:
    if inp.travellers <= 0 or inp.adults < 0:
        raise ValueError("There must be at least one traveller.")
    pax = Decimal(inp.travellers)
    warnings: list[str] = []
    unpriced: list[str] = []
    margin = {c: Decimal(inp.margins.get(c, ZERO)) / 100 for c in CATEGORIES}

    # Per-person cost by category (adult twin, excluding the hotel twin share) and actual group cost.
    pp: dict[str, Decimal] = {c: ZERO for c in CATEGORIES}
    group_cost: dict[str, Decimal] = {c: ZERO for c in CATEGORIES}
    for line in inp.lines:
        if not line.included:
            continue
        if line.unit_cost is None:
            unpriced.append(line.description)
            continue
        cat = line.category if line.category in CATEGORIES else "other"
        total = line_group_total(line, inp.travellers) or ZERO
        group_cost[cat] += total
        if line.basis == "per_person":
            pp[cat] += line.unit_cost * line.quantity
        elif line.basis in SHARED_BASES:
            pp[cat] += total / pax
        # per_room (hotel rooms) is priced through the stay rates below, not per line.

    twin_share = ZERO
    single_extra = ZERO
    for s in inp.stays:
        if s.double_rate is None:
            unpriced.append(f"Room rate: {s.label}")
            continue
        twin = s.double_rate / 2
        twin_share += twin * s.nights
        single = s.single_rate if s.single_rate is not None else s.double_rate
        single_extra += (single - twin) * s.nights
        if s.single_is_estimate:
            warnings.append(f"{s.label}: no single-room rate; the double room rate is used for single use (estimate).")

    hotel_m = margin["hotel"]
    non_hotel_selling = sum((pp[c] * (1 + margin[c]) for c in CATEGORIES), ZERO)
    non_hotel_cost = sum(pp.values(), ZERO)
    adult_cost = non_hotel_cost + twin_share
    adult = non_hotel_selling + twin_share * (1 + hotel_m)
    child_bed = non_hotel_selling + twin_share * inp.child_bed_pct / 100 * (1 + hotel_m)
    child_nobed = non_hotel_selling
    supplement = single_extra * (1 + hotel_m)

    factor = 1 - inp.discount_pct / 100

    def finish(v: Decimal, adjust: bool = True) -> Decimal:
        v = v * factor + (inp.adjustment_per_person if adjust else ZERO)
        return round_up(max(v, ZERO), inp.rounding)

    adult_p = finish(adult) if inp.adults else None
    supp_p = finish(supplement, adjust=False) if inp.stays else None
    cwb = finish(child_bed) if inp.children_with_bed else None
    cnb = finish(child_nobed) if inp.children_without_bed else None

    revenue = (adult_p or ZERO) * inp.adults + (supp_p or ZERO) * inp.singles + (cwb or ZERO) * inp.children_with_bed + (cnb or ZERO) * inp.children_without_bed

    # Actual hotel cost comes from the real room plan (per_room lines).
    total_cost = sum(group_cost.values(), ZERO)
    profit = revenue - total_cost
    pct = _q(profit / revenue * 100) if revenue > 0 else None
    if unpriced:
        warnings.insert(0, f"{len(unpriced)} cost item(s) have no price yet: the prices are incomplete.")
    if pct is not None and pct < 0:
        warnings.append("The selling prices are below cost.")
    if inp.singles > inp.adults:
        warnings.append("More single rooms than adults.")

    categories = []
    for c in CATEGORIES:
        part = pp[c] + (twin_share if c == "hotel" else ZERO)
        if group_cost[c] or part:
            categories.append(CategoryResult(c, _q(group_cost[c]), _q(margin[c] * 100), _q(part), _q(part * (1 + margin[c]))))
    return PricingResult(
        adult_twin=adult_p, single_supplement=supp_p, child_with_bed=cwb, child_without_bed=cnb,
        adult_twin_cost=_q(adult_cost), categories=categories, total_cost=_q(total_cost), revenue=_q(revenue),
        profit=_q(profit), margin_on_revenue_pct=pct, unpriced=unpriced, warnings=warnings,
    )


def convert(amount: Decimal | None, rate: Decimal | None, unit: Decimal = Decimal(1)) -> Decimal | None:
    """Amount in another currency at a manually entered rate (1 base = rate), rounded up."""
    if amount is None or not rate:
        return None
    return round_up(amount * rate, unit)
