"""Version list and human-readable comparison between two versions (PRD 14.5)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attraction, City, Hotel, Itinerary, User, Vehicle
from app.schemas.itinerary import VersionDiff, VersionInfo
from app.services.itinerary_checks import evaluate
from app.services.itinerary_service import ItineraryService


def versions(db: Session, it: Itinerary) -> list[VersionInfo]:
    service = ItineraryService(db)
    users = {u.id: u.full_name for u in db.scalars(select(User))}
    out = []
    for meta in sorted(it.versions, key=lambda v: v.version_number, reverse=True):
        v = service.current_version(it, meta.version_number)
        ev = evaluate(db, v, it.enquiry_id)
        out.append(VersionInfo(version_number=v.version_number, label=v.label, notes=v.notes, is_locked=v.is_locked,
                               created_at=v.created_at, created_by=users.get(v.created_by_id), total_days=v.total_days,
                               total_nights=v.total_nights, total_cost=str(ev.total_cost.quantize(Decimal("1"))), currency=ev.currency))
    return out


def compare(db: Session, it: Itinerary, a: int, b: int) -> VersionDiff:
    service = ItineraryService(db)
    va, vb = service.current_version(it, a), service.current_version(it, b)
    city = {c.id: c.name for c in db.scalars(select(City))}
    hotel = {h.id: h.name for h in db.scalars(select(Hotel))}
    att = {x.id: x.name for x in db.scalars(select(Attraction))}
    veh = {x.id: x.name for x in db.scalars(select(Vehicle))}

    def nights(v):
        out: dict[int, int] = {}
        for s in v.stays:
            out[s.city_id] = out.get(s.city_id, 0) + s.nights
        return out

    def hotels(v):
        return {s.city_id: s.hotel_id for s in v.stays}

    def sights(v):
        return {x.attraction_id for d in v.days for x in d.activities if x.attraction_id}

    summary = []
    if va.total_days != vb.total_days:
        diff = vb.total_days - va.total_days
        summary.append(f"Trip length: {va.total_days} → {vb.total_days} days ({'+' if diff > 0 else ''}{diff}).")
    na, nb = nights(va), nights(vb)
    for cid in list(dict.fromkeys([*na, *nb])):
        if cid not in na:
            summary.append(f"Added {city.get(cid, cid)} ({nb[cid]} night{'s' if nb[cid] != 1 else ''}).")
        elif cid not in nb:
            summary.append(f"Removed {city.get(cid, cid)}.")
        elif na[cid] != nb[cid]:
            summary.append(f"{city.get(cid, cid)}: {na[cid]} → {nb[cid]} nights.")
    ha, hb = hotels(va), hotels(vb)
    for cid in nb:
        if cid in ha and ha[cid] != hb[cid]:
            summary.append(f"{city.get(cid, cid)} hotel: {hotel.get(ha[cid], 'none')} → {hotel.get(hb[cid], 'none')}.")
    sa, sb = sights(va), sights(vb)
    if sb - sa:
        summary.append("Sightseeing added: " + ", ".join(sorted(att.get(x, str(x)) for x in sb - sa)) + ".")
    if sa - sb:
        summary.append("Sightseeing removed: " + ", ".join(sorted(att.get(x, str(x)) for x in sa - sb)) + ".")
    if va.vehicle_id != vb.vehicle_id:
        summary.append(f"Vehicle: {veh.get(va.vehicle_id, 'none')} → {veh.get(vb.vehicle_id, 'none')}.")
    ea, eb = evaluate(db, va, it.enquiry_id), evaluate(db, vb, it.enquiry_id)
    if ea.total_cost != eb.total_cost:
        d = eb.total_cost - ea.total_cost
        summary.append(f"Estimated total: {ea.total_cost:,.0f} → {eb.total_cost:,.0f} {eb.currency} ({'+' if d > 0 else ''}{d:,.0f}).")
    if not summary:
        summary.append("No differences in days, cities, hotels, sightseeing, vehicle or estimated cost.")

    def route(v):
        return [f"{city.get(s.city_id, s.city_id)} {s.nights}N" for s in sorted(v.stays, key=lambda s: s.check_in_day)]

    return VersionDiff(a=a, b=b, summary=summary, route_a=route(va), route_b=route(vb),
                       cost_a=str(ea.total_cost.quantize(Decimal("1"))), cost_b=str(eb.total_cost.quantize(Decimal("1"))), currency=eb.currency)
