"""Pricing & costing (Phase 7).

Automatic cost lines are rebuilt from the itinerary version on every read, so
the prices follow edits in the builder. Planner decisions (margins, overrides,
manual lines...) live in the version's `PricingSheet`. Costs are inventory
estimates unless the source price is marked verified.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError
from app.engines.pricing import CATEGORIES, CostLine, PricingInput, StayRate, convert, line_group_total, price
from app.models import (
    AppSetting, Attraction, City, Hotel, Itinerary, ItineraryVersion, PricingLine, PricingSheet, Restaurant, Supplier, SupplierRate, User,
    Vehicle,
)
from app.schemas.pricing import (
    CATEGORY_LABELS, CategoryOut, CustomerPrice, LineOut, LineOverride, ManualLineIn, PricingDefaults, PricingSettingsUpdate,
    PricingView, Prices, QuoteIn, StayRateOut, StayRateOverride,
)
from app.services.itinerary_service import ItineraryService
from app.services.requirement_service import RequirementService

DEFAULTS_KEY = "pricing_defaults"
MANUAL_PREFIX = "manual:"


def _s(v: Decimal | None) -> str | None:
    return None if v is None else str(v)


def _cents(v: Decimal | None) -> Decimal | None:
    return None if v is None else v.quantize(Decimal("0.01"))


def _dec(v) -> Decimal | None:
    return None if v is None or v == "" else Decimal(str(v))


class PricingService:
    def __init__(self, db: Session, user: User | None = None):
        self.db = db
        self.user = user
        self.itineraries = ItineraryService(db)

    # ------------------------------------------------------------------ defaults (admin)
    def defaults(self) -> PricingDefaults:
        row = self.db.scalar(select(AppSetting).where(AppSetting.key == DEFAULTS_KEY))
        return PricingDefaults.model_validate(row.value) if row and isinstance(row.value, dict) else PricingDefaults()

    def save_defaults(self, data: PricingDefaults) -> PricingDefaults:
        row = self.db.scalar(select(AppSetting).where(AppSetting.key == DEFAULTS_KEY))
        if row is None:
            row = AppSetting(key=DEFAULTS_KEY, description="Pricing defaults: margins per category, rounding, child bed share, display currency")
            self.db.add(row)
        data = data.model_copy(update={"margins": {c: data.margins.get(c, Decimal(0)) for c in CATEGORIES}})
        row.value = data.model_dump(mode="json")
        self.db.commit()
        return data

    # ------------------------------------------------------------------ sheet lifecycle
    def _version(self, itinerary_id: int, version_number: int | None) -> tuple[Itinerary, ItineraryVersion]:
        it = self.itineraries.get(itinerary_id)
        return it, self.itineraries.current_version(it, version_number)

    def _sheet(self, v: ItineraryVersion, create: bool = True) -> PricingSheet | None:
        sheet = self.db.scalar(select(PricingSheet).options(selectinload(PricingSheet.lines)).where(PricingSheet.version_id == v.id))
        if sheet is None and create:
            d = self.defaults()
            sheet = PricingSheet(version_id=v.id, margins={k: str(x) for k, x in d.margins.items()}, rounding=d.rounding,
                                 child_bed_pct=d.child_bed_pct, display_currency=d.display_currency, exchange_rate=d.exchange_rate,
                                 overrides={}, stay_overrides={}, fx_rates={}, updated_by_id=self.user.id if self.user else None)
            self.db.add(sheet)
            self.db.commit()
            sheet = self.db.scalar(select(PricingSheet).options(selectinload(PricingSheet.lines)).where(PricingSheet.version_id == v.id))
        return sheet

    def copy_sheet(self, src: ItineraryVersion, dst: ItineraryVersion) -> None:
        """Carry the planner's pricing decisions to a new version (start editing, restore, duplicate)."""
        sheet = self._sheet(src, create=False)
        if sheet is None:
            return
        new = PricingSheet(
            version_id=dst.id, currency=sheet.currency, margins=dict(sheet.margins), discount_pct=sheet.discount_pct,
            adjustment_per_person=sheet.adjustment_per_person, rounding=sheet.rounding, child_bed_pct=sheet.child_bed_pct,
            adults=sheet.adults, children_with_bed=sheet.children_with_bed, children_without_bed=sheet.children_without_bed,
            singles=sheet.singles, overrides=dict(sheet.overrides), stay_overrides=dict(sheet.stay_overrides),
            display_currency=sheet.display_currency, exchange_rate=sheet.exchange_rate, pdf_currency=sheet.pdf_currency,
            notes=sheet.notes, updated_by_id=sheet.updated_by_id, fx_rates=dict(sheet.fx_rates or {}),
        )
        new.lines = [PricingLine(category=l.category, basis=l.basis, description=l.description, unit_cost=l.unit_cost, quantity=l.quantity,
                                 is_estimate=l.is_estimate, supplier_id=l.supplier_id, sort_order=l.sort_order, quote=l.quote) for l in sheet.lines]
        self.db.add(new)

    # ------------------------------------------------------------------ automatic lines
    def _auto(self, it: Itinerary, v: ItineraryVersion, currency: str) -> tuple[list[CostLine], list[StayRate], list[str]]:
        notes: list[str] = []
        days = sorted(v.days, key=lambda d: d.day_number)
        city_ids = {s.city_id for s in v.stays} | {t.from_city_id for t in v.transports if t.from_city_id} | {t.to_city_id for t in v.transports if t.to_city_id}
        cities = {c.id: c.name for c in self.db.scalars(select(City).where(City.id.in_(city_ids or {0})))}
        hotels = {h.id: h for h in self.db.scalars(
            select(Hotel).options(selectinload(Hotel.room_types), selectinload(Hotel.rates)).where(Hotel.id.in_({s.hotel_id for s in v.stays if s.hotel_id} or {0})))}
        lines: list[CostLine] = []
        stays: list[StayRate] = []

        def money(amount, cur: str, what: str) -> Decimal | None:
            if amount is None:
                return None
            if cur != currency:
                notes.append(f"{what}: price is in {cur}, not {currency}. Enter it in {currency} to include it.")
                return None
            return Decimal(amount)

        # Hotels: actual room plan (cost) and the twin/single rates (per-person prices).
        for s in sorted(v.stays, key=lambda x: x.check_in_day):
            city = cities.get(s.city_id, "?")
            h = hotels.get(s.hotel_id)
            check_in = next((d.date for d in days if d.day_number == s.check_in_day), v.start_date)
            if h is None:
                lines.append(CostLine(f"hotel:{s.city_id}:none", "hotel", "per_room", f"Hotel to be selected in {city}, {s.nights} nights", None, Decimal(s.nights)))
                stays.append(StayRate(f"stay:{s.city_id}:none", f"Hotel in {city}", s.nights, None, None))
                continue
            types = {rt.id: rt for rt in h.room_types}
            for r in s.rooms or []:
                rt = types.get(r.get("room_type_id"))
                unit = money(r.get("price"), rt.currency if rt else "EUR", f"{h.name} {r.get('label')}")
                verified = bool(rt and rt.price_is_verified)
                lines.append(CostLine(f"hotel:{s.city_id}:{h.id}:{r.get('room_type_id') or r.get('label')}", "hotel", "per_room",
                                      f"{h.name}, {city}: {r.get('label', 'Room')} × {r.get('count', 1)}, {s.nights} night{'s' if s.nights != 1 else ''}",
                                      unit, Decimal(r.get("count", 1) * s.nights), is_estimate=not verified, supplier_id=h.supplier_id))

            def rate(rt) -> Decimal | None:
                seasonal = next((x for x in h.rates if x.room_type_id == rt.id and x.valid_from <= check_in <= x.valid_to), None)
                if seasonal:
                    return money(seasonal.price, seasonal.currency, f"{h.name} {rt.name}")
                return money(rt.base_price, rt.currency, f"{h.name} {rt.name}")

            doubles = [rt for rt in h.room_types if rt.max_occupancy == 2]
            doubles.sort(key=lambda rt: (not any(w in rt.name.lower() for w in ("double", "twin")), rt.base_price or Decimal(10**9)))
            singles = [rt for rt in h.room_types if rt.max_occupancy == 1 or "single" in rt.name.lower()]
            double_rate = rate(doubles[0]) if doubles else None
            single_rate = rate(singles[0]) if singles else None
            stays.append(StayRate(f"stay:{s.city_id}:{h.id}", f"{h.name}, {city}", s.nights, double_rate, single_rate,
                                  single_is_estimate=single_rate is None and double_rate is not None))

        # Vehicle (shared by the group).
        vehicle = self.db.get(Vehicle, v.vehicle_id) if v.vehicle_id else None
        if vehicle:
            if vehicle.price_per_day is not None:
                lines.append(CostLine(f"vehicle:{vehicle.id}:day", "transport", "per_day", f"{vehicle.name}, {v.total_days} days",
                                      money(vehicle.price_per_day, vehicle.currency, vehicle.name), Decimal(v.total_days), not vehicle.price_is_verified, supplier_id=vehicle.supplier_id))
                if vehicle.driver_cost_per_day:
                    lines.append(CostLine(f"vehicle:{vehicle.id}:driver", "transport", "per_day", f"Driver for {vehicle.name}, {v.total_days} days",
                                          money(vehicle.driver_cost_per_day, vehicle.currency, "Driver"), Decimal(v.total_days), not vehicle.price_is_verified, supplier_id=vehicle.supplier_id))
            elif vehicle.price_per_km is not None:
                km = sum(t.distance_km or 0 for t in v.transports if t.mode != "train")
                lines.append(CostLine(f"vehicle:{vehicle.id}:km", "transport", "per_km", f"{vehicle.name}, about {km} km",
                                      money(vehicle.price_per_km, vehicle.currency, vehicle.name), Decimal(km), True, supplier_id=vehicle.supplier_id))
            else:
                lines.append(CostLine(f"vehicle:{vehicle.id}:day", "transport", "per_day", f"{vehicle.name}, {v.total_days} days (no price in inventory)",
                                      None, Decimal(v.total_days), supplier_id=vehicle.supplier_id))
        for t in v.transports:
            if t.mode == "train":
                lines.append(CostLine(f"train:{t.from_city_id}:{t.to_city_id}", "transport", "per_person",
                                      f"Train {cities.get(t.from_city_id, '?')} → {cities.get(t.to_city_id, '?')}", None, Decimal(1)))

        # Sightseeing tickets (per person, once per visit).
        visits = Counter(a.attraction_id for d in days for a in d.activities if a.attraction_id)
        attractions = {a.id: a for a in self.db.scalars(select(Attraction).where(Attraction.id.in_(set(visits) or {0})))}
        for aid, n in sorted(visits.items()):
            a = attractions.get(aid)
            if a and a.ticket_required:
                lines.append(CostLine(f"ticket:{aid}", "sightseeing", "per_person", f"{a.name} tickets",
                                      money(a.ticket_price, a.currency, a.name), Decimal(n), not a.price_is_verified, supplier_id=a.supplier_id))

        # Meals at restaurants (per person per meal) and at hotels (no price in inventory).
        meals = Counter(m.restaurant_id for d in days for m in d.meals if m.arrangement == "restaurant" and m.restaurant_id)
        restaurants = {r.id: r for r in self.db.scalars(select(Restaurant).where(Restaurant.id.in_(set(meals) or {0})))}
        for rid, n in sorted(meals.items()):
            r = restaurants.get(rid)
            if r:
                lines.append(CostLine(f"meal:{rid}", "meal", "per_person", f"{r.name}: {n} meal{'s' if n != 1 else ''}",
                                      money(r.avg_price_per_person, r.currency, r.name), Decimal(n), not getattr(r, "price_is_verified", False), supplier_id=r.supplier_id))
        hotel_meals = Counter(m.meal for d in days for m in d.meals if m.arrangement == "hotel" and m.meal != "breakfast")
        for meal, n in sorted(hotel_meals.items()):
            lines.append(CostLine(f"hotelmeal:{meal}", "meal", "per_person", f"{meal.title()} at the hotel: {n}", None, Decimal(n)))
        return lines, stays, notes

    # ------------------------------------------------------------------ calculation
    def _travellers(self, it: Itinerary) -> dict[str, int]:
        if not it.enquiry_id:
            return {"adults": 2, "children": 0, "singles": 0}
        req = RequirementService(self.db).get(it.enquiry_id)
        singles = sum(r.count for r in req.rooms if r.type == "single")
        return {"adults": req.adults, "children": req.children, "singles": singles}

    def _compute(self, it: Itinerary, v: ItineraryVersion, sheet: PricingSheet):
        auto, stays, notes = self._auto(it, v, sheet.currency)
        out_lines: list[LineOut] = []
        engine_lines: list[CostLine] = []
        trav = self._travellers(it)
        adults = sheet.adults if sheet.adults is not None else trav["adults"]
        cwb = sheet.children_with_bed if sheet.children_with_bed is not None else trav["children"]
        cnb = sheet.children_without_bed if sheet.children_without_bed is not None else 0
        singles = sheet.singles if sheet.singles is not None else trav["singles"]
        pax = adults + cwb + cnb

        supplier_names = {sid: n for sid, n in self.db.execute(select(Supplier.id, Supplier.name))}

        def status_of(quote: dict | None, line: CostLine) -> str:
            if quote and quote.get("status"):
                return quote["status"]
            return "estimate" if line.unit_cost is None or line.is_estimate else "quoted"

        for line in auto:
            o = sheet.overrides.get(line.key) or {}
            original = line.unit_cost
            if "unit_cost" in o:
                line.unit_cost = _dec(o["unit_cost"])
            if o.get("quantity") is not None:
                line.quantity = Decimal(str(o["quantity"]))
            if "included" in o:
                line.included = bool(o["included"])
            quote = o.get("quote")
            if quote:
                line.is_estimate = quote.get("status") == "estimate"
            supplier_id = (quote or {}).get("supplier_id") or line.supplier_id
            engine_lines.append(line)
            out_lines.append(LineOut(key=line.key, category=line.category, basis=line.basis, description=line.description,
                                     unit_cost=_s(line.unit_cost), quantity=str(line.quantity), total=_s(_cents(line_group_total(line, pax))),
                                     is_estimate=line.is_estimate and "unit_cost" not in o, included=line.included,
                                     is_overridden=bool(o), auto_unit_cost=_s(original), status=status_of(quote, line),
                                     supplier_id=supplier_id, supplier_name=supplier_names.get(supplier_id), quote=quote))
        for m in sheet.lines:
            line = CostLine(f"{MANUAL_PREFIX}{m.id}", m.category, m.basis, m.description, _dec(m.unit_cost), _dec(m.quantity) or Decimal(0), m.is_estimate)
            engine_lines.append(line)
            out_lines.append(LineOut(key=line.key, manual_id=m.id, category=m.category, basis=m.basis, description=m.description,
                                     unit_cost=_s(_dec(m.unit_cost)), quantity=str(m.quantity), total=_s(_cents(line_group_total(line, pax))),
                                     is_estimate=m.is_estimate, included=True, status=status_of(m.quote, line),
                                     supplier_id=m.supplier_id, supplier_name=supplier_names.get(m.supplier_id), quote=m.quote))
        stay_out = []
        for s in stays:
            o = sheet.stay_overrides.get(s.key) or {}
            if o.get("double_rate") is not None:
                s.double_rate = Decimal(str(o["double_rate"]))
            if o.get("single_rate") is not None:
                s.single_rate = Decimal(str(o["single_rate"]))
                s.single_is_estimate = False
            stay_out.append(StayRateOut(key=s.key, label=s.label, nights=s.nights, double_rate=_s(s.double_rate), single_rate=_s(s.single_rate),
                                        single_is_estimate=s.single_is_estimate, is_overridden=bool(o)))

        inp = PricingInput(adults=adults, children_with_bed=cwb, children_without_bed=cnb, singles=singles,
                           margins={k: Decimal(str(x)) for k, x in sheet.margins.items()}, discount_pct=_dec(sheet.discount_pct) or Decimal(0),
                           adjustment_per_person=_dec(sheet.adjustment_per_person) or Decimal(0), rounding=_dec(sheet.rounding) or Decimal(0),
                           child_bed_pct=_dec(sheet.child_bed_pct) if sheet.child_bed_pct is not None else Decimal(100),
                           lines=engine_lines, stays=stays)
        if pax <= 0:
            raise DomainError("Set at least one traveller to calculate prices.", status.HTTP_400_BAD_REQUEST, "no_travellers")
        result = price(inp)
        result.warnings[:0] = notes
        return result, out_lines, stay_out, dict(adults=adults, children_with_bed=cwb, children_without_bed=cnb, singles=singles), trav

    def _prices(self, result, currency: str) -> Prices:
        return Prices(currency=currency, adult_twin=_s(result.adult_twin), single_supplement=_s(result.single_supplement),
                      child_with_bed=_s(result.child_with_bed), child_without_bed=_s(result.child_without_bed))

    def _display(self, result, sheet: PricingSheet) -> Prices | None:
        if not sheet.display_currency or not sheet.exchange_rate or sheet.display_currency == sheet.currency:
            return None
        r = _dec(sheet.exchange_rate)
        return Prices(currency=sheet.display_currency, adult_twin=_s(convert(result.adult_twin, r)), single_supplement=_s(convert(result.single_supplement, r)),
                      child_with_bed=_s(convert(result.child_with_bed, r)), child_without_bed=_s(convert(result.child_without_bed, r)))

    # ------------------------------------------------------------------ public
    def view(self, itinerary_id: int, version_number: int | None = None) -> PricingView:
        it, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        result, lines, stays, trav, from_enquiry = self._compute(it, v, sheet)
        req = RequirementService(self.db).get(it.enquiry_id) if it.enquiry_id else None
        return PricingView(
            version_number=v.version_number, version_label=v.label, currency=sheet.currency,
            margins={c: str(Decimal(str(sheet.margins.get(c, 0)))) for c in CATEGORIES},
            discount_pct=str(_dec(sheet.discount_pct)), adjustment_per_person=str(_dec(sheet.adjustment_per_person)), rounding=str(_dec(sheet.rounding)),
            child_bed_pct=str(_dec(sheet.child_bed_pct)), **trav, travellers_from_enquiry=from_enquiry,
            display_currency=sheet.display_currency, exchange_rate=_s(sheet.exchange_rate), pdf_currency=sheet.pdf_currency, notes=sheet.notes,
            lines=lines, stays=stays,
            categories=[CategoryOut(category=c.category, label=CATEGORY_LABELS[c.category], cost=str(c.cost), margin_pct=str(c.margin_pct),
                                    per_person_cost=str(c.per_person_cost), per_person_selling=str(c.per_person_selling)) for c in result.categories],
            prices=self._prices(result, sheet.currency), display_prices=self._display(result, sheet),
            adult_twin_cost=str(result.adult_twin_cost), total_cost=str(result.total_cost), revenue=str(result.revenue), profit=str(result.profit),
            margin_on_revenue_pct=_s(result.margin_on_revenue_pct),
            budget_per_person=_s(req.budget_per_person) if req and req.budget_per_person else None,
            warnings=result.warnings, margins_reviewed=self.defaults().margins_reviewed,
            trip_start=v.start_date, fx_rates={k: str(x) for k, x in (sheet.fx_rates or {}).items()},
            quote_progress=self._progress(lines),
        )

    @staticmethod
    def _progress(lines: list[LineOut]) -> dict[str, int]:
        included = [l for l in lines if l.included]
        counts = {k: sum(1 for l in included if l.status == k) for k in ("confirmed", "quoted", "estimate")}
        return {**counts, "total": len(included)}

    def customer_price(self, it: Itinerary, v: ItineraryVersion) -> CustomerPrice | None:
        """Selling prices for proposals, or None if this version has not been priced yet."""
        sheet = self._sheet(v, create=False)
        if sheet is None:
            return None
        result = self._compute(it, v, sheet)[0]
        display = self._display(result, sheet)
        return CustomerPrice(base=self._prices(result, sheet.currency), display=display,
                             show=sheet.pdf_currency if display else "base",
                             has_children=bool(result.child_with_bed or result.child_without_bed), is_incomplete=bool(result.unpriced))

    def update(self, itinerary_id: int, body: PricingSettingsUpdate, version_number: int | None = None) -> PricingView:
        _, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        data = body.model_dump(exclude_unset=True)
        if "margins" in data and data["margins"] is not None:
            data["margins"] = {**sheet.margins, **{k: str(x) for k, x in data["margins"].items()}}
        for k, val in data.items():
            setattr(sheet, k, val)
        sheet.updated_by_id = self.user.id if self.user else None
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def override(self, itinerary_id: int, body: LineOverride, version_number: int | None = None) -> PricingView:
        _, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        o = dict(sheet.overrides.get(body.key) or {})
        if body.clear_unit_cost:
            o["unit_cost"] = None
        elif body.unit_cost is not None:
            o["unit_cost"] = str(body.unit_cost)
        if body.quantity is not None:
            o["quantity"] = str(body.quantity)
        if body.included is not None:
            o["included"] = body.included
        sheet.overrides = {**sheet.overrides, body.key: o}
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def reset_override(self, itinerary_id: int, key: str, version_number: int | None = None) -> PricingView:
        _, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        sheet.overrides = {k: x for k, x in sheet.overrides.items() if k != key}
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def stay_rate(self, itinerary_id: int, body: StayRateOverride, version_number: int | None = None) -> PricingView:
        _, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        if body.double_rate is None and body.single_rate is None:
            sheet.stay_overrides = {k: x for k, x in sheet.stay_overrides.items() if k != body.key}
        else:
            sheet.stay_overrides = {**sheet.stay_overrides, body.key: {"double_rate": _s(body.double_rate), "single_rate": _s(body.single_rate)}}
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def add_line(self, itinerary_id: int, body: ManualLineIn, version_number: int | None = None) -> PricingView:
        _, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        sheet.lines.append(PricingLine(**body.model_dump(), sort_order=len(sheet.lines)))
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def _manual(self, itinerary_id: int, line_id: int, version_number: int | None) -> PricingLine:
        _, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        line = next((l for l in sheet.lines if l.id == line_id), None)
        if line is None:
            raise DomainError("Cost line not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return line

    def update_line(self, itinerary_id: int, line_id: int, body: ManualLineIn, version_number: int | None = None) -> PricingView:
        line = self._manual(itinerary_id, line_id, version_number)
        for k, val in body.model_dump().items():
            setattr(line, k, val)
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def delete_line(self, itinerary_id: int, line_id: int, version_number: int | None = None) -> PricingView:
        line = self._manual(itinerary_id, line_id, version_number)
        self.db.delete(line)
        self.db.commit()
        return self.view(itinerary_id, version_number)

    # ------------------------------------------------------------------ supplier quotes (Phase 8c)
    def quote(self, itinerary_id: int, body: QuoteIn, version_number: int | None = None) -> PricingView:
        """Record a supplier's price for one line; converts to the sheet currency with the given exchange rate."""
        it, v = self._version(itinerary_id, version_number)
        sheet = self._sheet(v)
        if body.supplier_id is not None and self.db.get(Supplier, body.supplier_id) is None:
            raise DomainError("Supplier not found.", status.HTTP_400_BAD_REQUEST, "invalid_supplier")
        if body.supplier_rate_id is not None and self.db.get(SupplierRate, body.supplier_rate_id) is None:
            raise DomainError("Supplier rate not found.", status.HTTP_400_BAD_REQUEST, "invalid_rate")
        foreign = body.currency != sheet.currency
        fx = Decimal(1)
        if foreign:
            fx = body.fx_rate or _dec((sheet.fx_rates or {}).get(body.currency))
            if not fx:
                raise DomainError(f"Enter the exchange rate: 1 {body.currency} = ? {sheet.currency}.", status.HTTP_400_BAD_REQUEST, "fx_required")
            sheet.fx_rates = {**(sheet.fx_rates or {}), body.currency: str(fx)}
        unit = (body.amount * fx).quantize(Decimal("0.01"))
        quote = {"supplier_id": body.supplier_id, "supplier_rate_id": body.supplier_rate_id, "amount": str(body.amount), "currency": body.currency,
                 "fx_rate": str(fx) if foreign else None, "status": body.status, "reference": body.reference}
        if body.key.startswith(MANUAL_PREFIX):
            line = next((l for l in sheet.lines if f"{MANUAL_PREFIX}{l.id}" == body.key), None)
            if line is None:
                raise DomainError("Cost line not found.", status.HTTP_404_NOT_FOUND, "not_found")
            line.unit_cost, line.supplier_id, line.quote, line.is_estimate = unit, body.supplier_id, quote, body.status == "estimate"
            category, basis = line.category, line.basis
        else:
            auto = {l.key: l for l in self._auto(it, v, sheet.currency)[0]}
            if body.key not in auto:
                raise DomainError("Cost line not found.", status.HTTP_404_NOT_FOUND, "not_found")
            sheet.overrides = {**sheet.overrides, body.key: {**(sheet.overrides.get(body.key) or {}), "unit_cost": str(unit), "quote": quote}}
            category, basis = auto[body.key].category, auto[body.key].basis
        if body.save_as_rate and body.supplier_id and body.supplier_rate_id is None:
            self.db.add(SupplierRate(supplier_id=body.supplier_id, service=(body.service or body.key)[:200], category=category, basis=basis,
                                     unit_cost=body.amount, currency=body.currency, notes=body.reference))
        sheet.updated_by_id = self.user.id if self.user else None
        self.db.commit()
        return self.view(itinerary_id, version_number)

    def clear_quote(self, itinerary_id: int, key: str, version_number: int | None = None) -> PricingView:
        """Back to the inventory estimate (automatic lines) or an unquoted line (extra lines)."""
        if not key.startswith(MANUAL_PREFIX):
            return self.reset_override(itinerary_id, key, version_number)
        _, v = self._version(itinerary_id, version_number)
        line = next((l for l in self._sheet(v).lines if f"{MANUAL_PREFIX}{l.id}" == key), None)
        if line is None:
            raise DomainError("Cost line not found.", status.HTTP_404_NOT_FOUND, "not_found")
        line.quote, line.is_estimate = None, True
        self.db.commit()
        return self.view(itinerary_id, version_number)
