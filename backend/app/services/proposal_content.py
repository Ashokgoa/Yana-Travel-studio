"""Build the customer-facing proposal document from an itinerary version (Phase 6).

The output is a plain data structure the HTML templates render. It contains
only customer-safe information: no supplier names or costs, no internal notes,
no estimated inventory prices. The only price shown is the selling price the
planner typed into the designer.
"""

from __future__ import annotations

import base64
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.engines.route_map import MapStop, MapTheme, render_route_map
from app.models import Attraction, City, Enquiry, Hotel, Itinerary, ItineraryVersion, Media, MediaLink, Restaurant, TravelAgent, Vehicle
from app.schemas.proposal import BrandingSettings, ProposalSettings
from app.services.requirement_service import RequirementService
from app.services.storage import get_storage

FLAG_DIR = Path(__file__).resolve().parents[1] / "assets" / "flags"
TEMPLATE_COLOURS = {"explorer": ("#0F5257", "#F28C28")}  # classic and premium use the YANA brand colours
MEAL_NAMES = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}
MODE_PHRASES = {"coach": "private touring coach", "minibus": "private minibus", "car": "private car", "train": "train"}
STRATEGY_NAMES = {"classic": "Classic", "scenic": "Scenic", "premium": "Premium", "custom": "Tailor-made"}
SLOT_ORDER = {"morning": 0, "full_day": 1, "afternoon": 2, "evening": 3}

Segment = tuple[str, bool]  # (text, bold)


@dataclass
class DayBlock:
    number: int
    date_text: str
    heading: str
    subtitle: str | None
    flags: list[str]
    image: str | None
    bullets: list[list[Segment]]
    meals_line: str
    note: str | None


@dataclass
class ProposalDocument:
    template: str
    primary: str
    accent: str
    sections: list[str]
    title: str
    subtitle: str
    intro: str
    highlights: list[tuple[str, str]]
    route_text: str
    map_svg: str
    cover_image: str | None
    curated_line: str
    logos: list[str]
    contact_lines: list[str]
    days: list[DayBlock]
    hotels: list[dict]
    summary: list[dict]
    price: dict | None
    inclusions: list[str]
    exclusions: list[str]
    terms: list[str]
    closing: str
    reference: str | None
    version_label: str
    generated_on: str
    footer_text: str = ""
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------------- helpers
def default_title(it: Itinerary) -> str:
    """Short brochure title: the builder title before its detail ("Classic Europe: Netherlands, ... · 15 days")."""
    return it.title.split(":", 1)[0].strip() or it.title

def _join(items: list[str], last: str = " and ") -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + last + items[-1]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _fmt_date(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


@lru_cache(maxsize=128)
def flag_data_uri(iso: str | None) -> str | None:
    if not iso:
        return None
    path = FLAG_DIR / f"{iso.lower()}.svg"
    if not path.is_file():
        return None
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()


def _first_sentence(text: str | None, limit: int = 220) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    cut = text.find(". ")
    sentence = text if cut == -1 else text[: cut + 1]
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rsplit(" ", 1)[0] + "…"


def _cuisine_adjective(restaurant: Restaurant | None) -> str:
    """'Indian' for an Indian restaurant; otherwise a short cuisine word, or nothing."""
    if restaurant is None or not restaurant.cuisine:
        return ""
    c = restaurant.cuisine.strip()
    if "indian" in c.lower():
        return "Indian"
    return c if len(c) <= 18 and "," not in c else ""


class _Images:
    """Loads stored images once and returns them as resized data URIs."""

    def __init__(self, db: Session, enabled: bool = True):
        self.db = db
        self.enabled = enabled
        self.storage = get_storage()
        self._cache: dict[tuple[int, int], str | None] = {}

    def links(self, entity_type: str, ids: set[int]) -> dict[int, list[Media]]:
        if not ids:
            return {}
        rows = self.db.execute(
            select(MediaLink.entity_id, Media).join(Media, Media.id == MediaLink.media_id)
            .where(MediaLink.entity_type == entity_type, MediaLink.entity_id.in_(ids))
            .order_by(MediaLink.entity_id, MediaLink.is_primary.desc(), MediaLink.sort_order, MediaLink.id)
        ).all()
        out: dict[int, list[Media]] = {}
        for entity_id, media in rows:
            out.setdefault(entity_id, []).append(media)
        return out

    def data_uri(self, media: Media | None, max_px: int) -> str | None:
        if media is None or not self.enabled:
            return None
        key = (media.id, max_px)
        if key not in self._cache:
            self._cache[key] = self._encode(media, max_px)
        return self._cache[key]

    def _encode(self, media: Media, max_px: int) -> str | None:
        try:
            source = media.thumbnail_key if max_px <= 300 and media.thumbnail_key else media.storage_key
            raw = self.storage.read(source)
            with Image.open(io.BytesIO(raw)) as im:
                has_alpha = media.mime_type == "image/png" and source == media.storage_key  # logos keep PNG and transparency
                im = im.convert("RGBA" if has_alpha else "RGB")
                im.thumbnail((max_px, max_px))
                buf = io.BytesIO()
                if has_alpha:
                    im.save(buf, "PNG", optimize=True)
                    mime = "image/png"
                else:
                    im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
                    mime = "image/jpeg"
            return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:  # a missing or unreadable file must never break the whole PDF
            return None


# ---------------------------------------------------------------------------------- builder
class ProposalBuilder:
    def __init__(self, db: Session, with_images: bool = True):
        self.db = db
        self.images = _Images(db, enabled=with_images)

    def image_choices(self, version: ItineraryVersion) -> list[dict]:
        """For the designer: per day, the photos that can be used (attractions, hotel, city)."""
        ctx = self._context(version)
        out = []
        for d in version.days:
            choices = []
            for kind, eid in self._image_sources(d, ctx):
                for m in ctx["media"][kind].get(eid, []):
                    if all(c["media_id"] != m.id for c in choices):
                        choices.append({"media_id": m.id, "label": ctx["names"][kind].get(eid, ""), "kind": kind,
                                        "url": f"/api/v1/media/{m.id}/thumbnail?v={m.sha256[:12]}"})
            out.append({"day_number": d.day_number, "title": d.title, "choices": choices})
        return out

    # ------------------------------------------------------------------ data loading
    def _context(self, v: ItineraryVersion) -> dict:
        city_ids = {d.city_id for d in v.days} | {d.overnight_city_id for d in v.days if d.overnight_city_id} | {s.city_id for s in v.stays} \
            | {t.from_city_id for t in v.transports if t.from_city_id} | {t.to_city_id for t in v.transports if t.to_city_id}
        cities = {c.id: c for c in self.db.scalars(select(City).options(joinedload(City.country)).where(City.id.in_(city_ids or {0})))}
        hotel_ids = {s.hotel_id for s in v.stays if s.hotel_id}
        hotels = {h.id: h for h in self.db.scalars(select(Hotel).where(Hotel.id.in_(hotel_ids or {0})))}
        attraction_ids = {a.attraction_id for d in v.days for a in d.activities if a.attraction_id}
        attractions = {a.id: a for a in self.db.scalars(select(Attraction).where(Attraction.id.in_(attraction_ids or {0})))}
        restaurant_ids = {m.restaurant_id for d in v.days for m in d.meals if m.restaurant_id}
        restaurants = {r.id: r for r in self.db.scalars(select(Restaurant).where(Restaurant.id.in_(restaurant_ids or {0})))}
        media = {
            "attraction": self.images.links("attraction", attraction_ids),
            "hotel": self.images.links("hotel", hotel_ids),
            "city": self.images.links("city", set(cities)),
        }
        names = {
            "attraction": {i: a.name for i, a in attractions.items()},
            "hotel": {i: h.name for i, h in hotels.items()},
            "city": {i: c.name for i, c in cities.items()},
        }
        return dict(cities=cities, hotels=hotels, attractions=attractions, restaurants=restaurants, media=media, names=names)

    def _stay_for_night(self, v: ItineraryVersion, day_number: int):
        return next((s for s in v.stays if s.check_in_day <= day_number < s.check_in_day + s.nights), None)

    def _image_sources(self, d, ctx) -> list[tuple[str, int]]:
        sources = [("attraction", a.attraction_id) for a in d.activities if a.attraction_id]
        stay = self._stay_for_night(d.version, d.day_number)
        if stay and stay.hotel_id and any(a.activity_type == "check_in" for a in d.activities):
            sources.append(("hotel", stay.hotel_id))
        sources.append(("city", d.city_id))
        if stay and stay.hotel_id and ("hotel", stay.hotel_id) not in sources:
            sources.append(("hotel", stay.hotel_id))
        return sources

    # ------------------------------------------------------------------ main
    def build(self, it: Itinerary, v: ItineraryVersion, settings: ProposalSettings, branding: BrandingSettings) -> ProposalDocument:
        ctx = self._context(v)
        cities, hotels = ctx["cities"], ctx["hotels"]
        enquiry = self.db.scalar(
            select(Enquiry).options(joinedload(Enquiry.customer), joinedload(Enquiry.travel_agent)).where(Enquiry.id == it.enquiry_id)
        ) if it.enquiry_id else None
        req = RequirementService(self.db).get(it.enquiry_id) if it.enquiry_id else None
        vehicle = self.db.get(Vehicle, v.vehicle_id) if v.vehicle_id else None

        primary, accent = TEMPLATE_COLOURS.get(settings.template, (branding.primary_color, branding.accent_color))
        primary = settings.primary_color or primary
        accent = settings.accent_color or accent

        # Route: every city in day order (includes pass-through sightseeing cities).
        stops: list[City] = []
        for d in v.days:
            for cid in (d.city_id, d.overnight_city_id):
                c = cities.get(cid) if cid else None
                if c and (not stops or stops[-1].id != c.id):
                    stops.append(c)
        countries: list[tuple[str, str]] = []
        for c in stops:
            if (c.country.iso_code, c.country.name) not in countries:
                countries.append((c.country.iso_code, c.country.name))
        has_arrival = any(a.activity_type == "arrival" for a in v.days[0].activities) if v.days else False
        has_departure = any(a.activity_type == "departure" for a in v.days[-1].activities) if v.days else False

        travellers = (enquiry.adults + enquiry.children) if enquiry else None
        modes = Counter(t.mode for t in v.transports if t.mode != "train")
        road_mode = modes.most_common(1)[0][0] if modes else None
        uses_train = any(t.mode == "train" for t in v.transports)

        days = [self._day(d, v, ctx, settings, req) for d in v.days]

        # Text ----------------------------------------------------------------------------
        title = settings.title or default_title(it)
        subtitle = " · ".join([_plural(len(countries), "Country").replace("Countrys", "Countries"),
                               _plural(v.total_days, "Day"), _plural(v.total_nights, "Night")])
        sights = [a.title for d in v.days for a in d.activities if a.activity_type == "sightseeing"]
        country_text = _join([n for _, n in countries], " & ")
        if settings.intro:
            intro = settings.intro
        else:
            who = f" for {_plural(travellers, 'traveller')}" if travellers else ""
            top = _join(sights[:3]) if sights else "iconic sights"
            intro = (f"Discover {country_text} on a {v.total_days}-day journey{who}. "
                     f"This {STRATEGY_NAMES.get(it.strategy, '').lower() or 'tailor-made'} itinerary combines {top} "
                     f"with comfortable, seamless travel between {_plural(len(stops), 'destination')}.")

        meal_summary = self._meal_summary(v, ctx)
        highlights: list[tuple[str, str]] = [("Destinations", country_text), ("Duration", f"{_plural(v.total_days, 'Day')} / {_plural(v.total_nights, 'Night')}")]
        if travellers:
            detail = f" ({_plural(enquiry.adults, 'adult')}, {_plural(enquiry.children, 'child').replace('childs', 'children')})" if enquiry.children else ""
            highlights.insert(1, ("Group size", f"{_plural(travellers, 'traveller')}{detail}"))
        stars = sorted({hotels[s.hotel_id].star_rating for s in v.stays if s.hotel_id in hotels and hotels[s.hotel_id].star_rating})
        if stars:
            highlights.append(("Hotels", _join([f"{s}★" for s in stars]) + " hotels"))
        if meal_summary:
            highlights.append(("Meals", meal_summary))
        transport = MODE_PHRASES.get(road_mode or "", "")
        if transport or uses_train:
            text = transport[:1].upper() + transport[1:] if transport else ""
            highlights.append(("Transportation", _join([text, "train" if transport else "Train"] if uses_train else [text])))
        style = STRATEGY_NAMES.get(it.strategy, "Tailor-made") + " itinerary"
        if req and req.travel_type == "GIT":
            style += " · Group Inclusive Tour (GIT)"
        elif req and req.travel_type == "FIT":
            style += " · Independent travel (FIT)"
        highlights.append(("Tour style", style))

        route_names = [f"{c.name}, {c.country.name}" if i in (0,) or c.country.name != stops[i - 1].country.name else c.name for i, c in enumerate(stops)]
        route_text = " → ".join(route_names)
        if has_arrival:
            route_text = "Arrival " + route_text
        if has_departure and stops:
            route_text += " Departure"

        # Map (city photo, else the first trip sightseeing photo in that city).
        attraction_city = {}
        for d in v.days:
            for a in d.activities:
                if a.attraction_id and a.attraction_id in ctx["attractions"]:
                    attraction_city.setdefault(ctx["attractions"][a.attraction_id].city_id, a.attraction_id)
        map_stops = []
        for c in stops:
            media = (ctx["media"]["city"].get(c.id) or ctx["media"]["attraction"].get(attraction_city.get(c.id), []) or [None])[0]
            map_stops.append(MapStop(c.name, c.country.name, c.country.iso_code, c.latitude, c.longitude, self.images.data_uri(media, 240)))
        map_svg = render_route_map(
            map_stops, arrival_label="Arrival" if has_arrival else None, departure_label="Departure" if has_departure else None,
            flag_for=flag_data_uri, theme=MapTheme(route="#B3261E", pin=primary, label_bg=primary),
        ) if map_stops and all(s.lat is not None and s.lng is not None for s in map_stops) else ""

        # Branding ------------------------------------------------------------------------------
        agent: TravelAgent | None = enquiry.travel_agent if enquiry else None
        yana_logo = self.images.data_uri(self.db.get(Media, branding.logo_media_id), 600) if branding.logo_media_id else None
        logos, contact = [], []
        mode = settings.branding if agent or settings.branding == "yana" else "yana"
        if mode == "agent":
            curated = f"Curated by {agent.company_name}"
        elif mode == "both":
            curated = f"Curated by {agent.company_name} in partnership with {branding.company_name}"
        else:
            curated = f"Curated by {branding.company_name}"
        if mode in ("yana", "both") and yana_logo:
            logos.append(yana_logo)
        if mode in ("agent", "both") and agent:
            contact.append(" · ".join(x for x in (agent.company_name, agent.contact_person, agent.email, agent.phone) if x))
        if mode in ("yana", "both") and branding.contact_line:
            contact.append(f"{branding.company_name} · {branding.contact_line}")

        # Hotels, summary, price, inclusions -----------------------------------------------------
        hotel_rows = []
        for s in sorted(v.stays, key=lambda x: x.check_in_day):
            h = hotels.get(s.hotel_id)
            check_in = next((d.date for d in v.days if d.day_number == s.check_in_day), None)
            hotel_rows.append(dict(city=cities[s.city_id].name if s.city_id in cities else "", hotel=h.name if h else "To be confirmed",
                                   stars="★" * (h.star_rating or 0) if h and h.star_rating else "", nights=s.nights,
                                   dates=f"{_fmt_date(check_in)} – {_fmt_date(date.fromordinal(check_in.toordinal() + s.nights))}" if check_in else ""))

        summary = self._summary(v, ctx, days)

        price = self._price(it, v, settings)

        inclusions = settings.inclusions if settings.inclusions is not None else self._auto_inclusions(v, ctx, road_mode, uses_train, has_arrival, has_departure, stars)
        exclusions = settings.exclusions if settings.exclusions is not None else list(branding.default_exclusions)
        terms_text = settings.terms if settings.terms is not None else branding.default_terms

        cover_image = next((d.image for d in days if d.image), None)
        version_label = f"Version {v.version_number} · {v.label}"
        return ProposalDocument(
            template=settings.template, primary=primary, accent=accent,
            sections=[s.key for s in settings.sections if s.enabled],
            title=title, subtitle=subtitle, intro=intro, highlights=highlights, route_text=route_text, map_svg=map_svg,
            cover_image=cover_image, curated_line=curated, logos=logos, contact_lines=contact,
            days=days, hotels=hotel_rows, summary=summary, price=price,
            inclusions=inclusions, exclusions=exclusions, terms=[p.strip() for p in terms_text.splitlines() if p.strip()],
            closing=settings.closing or branding.default_closing,
            reference=enquiry.reference if enquiry else None, version_label=version_label,
            generated_on=_fmt_date(date.today()),
            footer_text=curated,
        )

    # ------------------------------------------------------------------ price
    def _price(self, it: Itinerary, v: ItineraryVersion, settings: ProposalSettings) -> dict:
        """Selling prices only: the planner's typed price, else the pricing sheet, else "Price on request"."""
        def money(currency: str, amount) -> str:
            d = Decimal(str(amount))
            return f"{currency} {d:,.0f}" if d == d.to_integral() else f"{currency} {d:,.2f}"

        if settings.price_per_person is not None:
            return dict(text=money(settings.price_currency, settings.price_per_person), per="per person", note=settings.price_note, rows=[])
        from app.services.pricing_service import PricingService  # local import: pricing depends on itinerary services

        cp = PricingService(self.db).customer_price(it, v)
        if cp is None or cp.base.adult_twin is None:
            return dict(text="Price on request", per=None, note=settings.price_note, rows=[])

        def text(field: str) -> str | None:
            base = getattr(cp.base, field)
            if base is None:
                return None
            shown = []
            if cp.show in ("base", "both"):
                shown.append(money(cp.base.currency, base))
            if cp.display and cp.show in ("display", "both") and getattr(cp.display, field) is not None:
                shown.append(money(cp.display.currency, getattr(cp.display, field)))
            return " · ".join(shown)

        labels = [("adult_twin", "Per adult, sharing a twin / double room"), ("single_supplement", "Single room supplement"),
                  ("child_with_bed", "Per child with a bed"), ("child_without_bed", "Per child without a bed")]
        rows = [(label, t) for field, label in labels if (t := text(field))]
        return dict(text=rows[0][1], per="per person", note=settings.price_note, rows=rows)

    # ------------------------------------------------------------------ days
    def _day(self, d, v: ItineraryVersion, ctx: dict, settings: ProposalSettings, req) -> DayBlock:
        cities, hotels, restaurants = ctx["cities"], ctx["hotels"], ctx["restaurants"]
        city = cities.get(d.city_id)
        transports = [t for t in v.transports if t.day_number == d.day_number]
        isos: list[str] = []
        for cid in [d.city_id, *[t.to_city_id for t in transports], d.overnight_city_id]:
            c = cities.get(cid) if cid else None
            if c and c.country.iso_code not in isos:
                isos.append(c.country.iso_code)
        flags = [f for f in (flag_data_uri(i) for i in isos) if f]

        stay = self._stay_for_night(v, d.day_number)
        hotel = hotels.get(stay.hotel_id) if stay and stay.hotel_id else None
        meals = {m.meal: m for m in d.meals}

        def meal_bullet(kind: str) -> list[Segment] | None:
            m = meals.get(kind)
            if m is None:
                return None
            name = MEAL_NAMES[kind]
            if m.arrangement == "hotel":
                return [(f"{name} at the hotel.", False)]
            if m.arrangement == "restaurant":
                adj = _cuisine_adjective(restaurants.get(m.restaurant_id))
                text = f"{adj} {name.lower()}" if adj else name
                return [(f"{text} at a local restaurant.", False)]
            return [(f"{name} at your own arrangement (not included).", False)]

        acts = sorted(d.activities, key=lambda a: (SLOT_ORDER.get(a.time_slot, 9), a.sort_order))
        before = [a for a in acts if a.time_slot in ("morning", "full_day")]
        after = [a for a in acts if a.time_slot == "afternoon"]
        evening = [a for a in acts if a.time_slot == "evening"]
        bullets: list[list[Segment]] = []
        if (b := meal_bullet("breakfast")):
            bullets.append(b)
        bullets += [self._activity(a, d, ctx, hotel, transports, settings) for a in before]
        if (b := meal_bullet("lunch")):
            bullets.append(b)
        bullets += [self._activity(a, d, ctx, hotel, transports, settings) for a in after]
        bullets += [self._activity(a, d, ctx, hotel, transports, settings) for a in evening if a.activity_type != "free_time"]
        if (b := meal_bullet("dinner")):
            bullets.append(b)
        bullets += [self._activity(a, d, ctx, hotel, transports, settings) for a in evening if a.activity_type == "free_time"]
        overnight = cities.get(d.overnight_city_id) if d.overnight_city_id else None
        if overnight:
            bullets.append([(f"Overnight in {overnight.name}.", False)])

        included = []
        for kind in ("breakfast", "lunch", "dinner"):
            m = meals.get(kind)
            if m and m.arrangement in ("hotel", "restaurant"):
                adj = _cuisine_adjective(restaurants.get(m.restaurant_id)) if m.arrangement == "restaurant" else ""
                included.append(f"{adj} {kind}" if adj else kind)
        meals_line = (_join(included)[:1].upper() + _join(included)[1:] + ".") if included else "Not included."

        sights = [a.title for a in d.activities if a.activity_type == "sightseeing"]
        legs = [t for t in transports if t.kind == "intercity"]
        if sights:
            subtitle = _join(sights, " & ")
        elif legs:
            subtitle = " · ".join(f"{cities[t.from_city_id].name} to {cities[t.to_city_id].name}" for t in legs if t.from_city_id in cities and t.to_city_id in cities)
        else:
            subtitle = None

        image = None
        override = settings.day_images.get(str(d.day_number))
        if override == 0:
            image = None
        elif override:
            media = self.db.get(Media, override)
            image = self.images.data_uri(media, 1400)
        else:
            for kind, eid in self._image_sources(d, ctx):
                lst = ctx["media"][kind].get(eid)
                if lst:
                    image = self.images.data_uri(lst[0], 1400)
                    break

        return DayBlock(number=d.day_number, date_text=d.date.strftime("%A, ") + _fmt_date(d.date), heading=d.title,
                        subtitle=subtitle if subtitle and subtitle != d.title else None, flags=flags, image=image,
                        bullets=bullets, meals_line=meals_line, note=d.description)

    def _activity(self, a, d, ctx, hotel, transports, settings) -> list[Segment]:
        cities = ctx["cities"]
        city = cities.get(d.city_id)
        if a.activity_type == "check_in":
            where = cities.get(d.overnight_city_id or d.city_id)
            if hotel and settings.hotel_names_in_days:
                stars = f" {'★' * hotel.star_rating}" if hotel.star_rating else ""
                return [("Check in at ", False), (hotel.name, True), (f"{stars}" + (f", {where.name}." if where else "."), False)]
            return [(f"Check in to your hotel{f' in {where.name}' if where else ''}.", False)]
        if a.activity_type == "check_out":
            return [("Check out of the hotel.", False)]
        if a.activity_type == "transfer":
            leg = next((t for t in transports if t.kind == "intercity"), None)
            dest = cities.get(leg.to_city_id) if leg and leg.to_city_id else None
            mode = MODE_PHRASES.get(leg.mode, "private transport") if leg else "private transport"
            if dest:
                extra = ""
                if leg.distance_km:
                    hours = (leg.duration_min or 0) / 60
                    extra = f" (about {leg.distance_km} km" + (f", around {hours:.0f} h" if hours >= 1 else "") + ")"
                return [(f"Travel by {mode} to ", False), (dest.name, True), (f"{extra}.", False)]
            return [(a.title.rstrip(".") + ".", False)]
        if a.activity_type == "sightseeing":
            attraction = ctx["attractions"].get(a.attraction_id) if a.attraction_id else None
            # Engine planning notes ("Seasonal: ... confirm dates") are for planners, not customers.
            own = a.description if a.description and not a.description.startswith("Seasonal:") else None
            desc = own or _first_sentence(attraction.description if attraction else None)
            segs: list[Segment] = [("Visit ", False), (a.title, True)]
            if desc:
                segs.append((f": {desc.rstrip('.')}.", False))
            else:
                segs.append(((f" in {city.name}." if city and city.name not in a.title else "."), False))
            return segs
        text = a.title.rstrip(".")
        if a.description:
            text += ". " + a.description.rstrip(".")
        return [(text + ".", False)]

    # ------------------------------------------------------------------ summaries
    def _meal_summary(self, v: ItineraryVersion, ctx) -> str:
        breakfasts = lunches = dinners = 0
        cuisines: Counter[str] = Counter()
        for d in v.days:
            for m in d.meals:
                if m.arrangement not in ("hotel", "restaurant"):
                    continue
                if m.meal == "breakfast":
                    breakfasts += 1
                elif m.meal == "lunch":
                    lunches += 1
                else:
                    dinners += 1
                if m.arrangement == "restaurant":
                    adj = _cuisine_adjective(ctx["restaurants"].get(m.restaurant_id))
                    if adj:
                        cuisines[adj] += 1
        parts = []
        if breakfasts:
            parts.append("daily breakfast" if breakfasts >= v.total_nights else _plural(breakfasts, "breakfast").replace("breakfasts", "breakfasts"))
        main = [x for x, n in (("lunch", lunches), ("dinner", dinners)) if n]
        if main:
            cuisine = cuisines.most_common(1)[0][0] + " " if cuisines else ""
            parts.append(f"{cuisine}{_join(main)}".strip())
        text = "; ".join(parts)
        return text[:1].upper() + text[1:] if text else ""

    def _summary(self, v: ItineraryVersion, ctx, days: list[DayBlock]) -> list[dict]:
        cities = ctx["cities"]
        rows = []
        last = len(v.days)
        for d, block in zip(v.days, days):
            city = cities.get(d.city_id)
            if not city:
                continue
            if d.day_number == 1 and any(a.activity_type == "arrival" for a in d.activities):
                text = f"{city.name} – Arrival & overnight stay"
            elif d.day_number == last and any(a.activity_type == "departure" for a in d.activities):
                text = f"{city.name} – Departure"
            else:
                what = block.subtitle or d.title
                stay_note = "" if d.overnight_city_id == d.city_id else " (no overnight stay)" if d.overnight_city_id else ""
                text = f"{city.name} – {what}{stay_note}" if city.name not in what else f"{what}{stay_note}"
            rows.append(dict(iso=city.country.iso_code, country=city.country.name, day=d.day_number, text=text))
            if d.overnight_city_id and d.overnight_city_id != d.city_id and d.overnight_city_id in cities:
                o = cities[d.overnight_city_id]
                rows.append(dict(iso=o.country.iso_code, country=o.country.name, day=d.day_number, text=f"{o.name} – Arrival & overnight stay"))
        # Country cell shown once per run of the same country (rowspan in the template).
        for i, r in enumerate(rows):
            r["flag"] = flag_data_uri(r["iso"])
            r["first"] = i == 0 or rows[i - 1]["country"] != r["country"]
            if r["first"]:
                span = 1
                while i + span < len(rows) and rows[i + span]["country"] == r["country"]:
                    span += 1
                r["span"] = span
        return rows

    def _auto_inclusions(self, v, ctx, road_mode, uses_train, has_arrival, has_departure, stars) -> list[str]:
        out = []
        star_text = (_join([f"{s}★" for s in stars], " / ") + " ") if stars else ""
        breakfast = any(m.meal == "breakfast" and m.arrangement == "hotel" for d in v.days for m in d.meals)
        out.append(f"{_plural(v.total_nights, 'night')} accommodation in {star_text}hotels (or similar)" + (" with daily breakfast" if breakfast else ""))
        lunches = sum(1 for d in v.days for m in d.meals if m.meal == "lunch" and m.arrangement in ("hotel", "restaurant"))
        dinners = sum(1 for d in v.days for m in d.meals if m.meal == "dinner" and m.arrangement in ("hotel", "restaurant"))
        if lunches or dinners:
            cuisines = Counter(_cuisine_adjective(ctx["restaurants"].get(m.restaurant_id)) for d in v.days for m in d.meals if m.arrangement == "restaurant")
            cuisines.pop("", None)
            c = f" ({cuisines.most_common(1)[0][0]} cuisine)" if cuisines else ""
            out.append(f"Meals as per the itinerary: {_join([x for x in (_plural(lunches, 'lunch').replace('lunchs', 'lunches') if lunches else '', _plural(dinners, 'dinner') if dinners else '') if x])}{c}")
        if road_mode:
            out.append(f"{MODE_PHRASES[road_mode][:1].upper() + MODE_PHRASES[road_mode][1:]} for transfers and sightseeing as per the itinerary")
        if uses_train:
            out.append("Train travel where shown in the itinerary")
        if has_arrival or has_departure:
            out.append(_join([x for x in ("Arrival" if has_arrival else "", "departure" if has_departure else "") if x]) + " airport transfers")
        tickets = []
        for d in v.days:
            for a in d.activities:
                at = ctx["attractions"].get(a.attraction_id) if a.attraction_id else None
                if at and at.ticket_required and a.title not in tickets:
                    tickets.append(a.title)
        if tickets:
            out.append("Entrance tickets: " + _join(tickets))
        out.append("Sightseeing as per the itinerary")
        return out
