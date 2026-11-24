"""Offline requirement reader (Phase 8): pulls travel requirements out of free
text such as an agent's email, with simple, explainable rules. No network.

It returns the same `ExtractedRequirements` shape as the optional Claude
provider, with `evidence` snippets so a planner can see where each value came
from. Nothing is applied automatically: the planner accepts or rejects each
suggestion. Unknown means None, never a guess.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

Food = Literal["indian_vegetarian", "indian_jain", "indian_non_vegetarian", "halal", "vegan", "continental", "mixed"]
Interest = Literal["historical_landmarks", "nature", "mountains", "lakes", "scenic", "museums", "shopping", "adventure",
                   "theme_parks", "cultural", "photography", "leisure", "family"]
Transport = Literal["private_coach", "luxury_coach", "mini_bus", "private_car", "train", "mixed"]
HotelCategory = Literal["3_star", "4_star", "5_star", "boutique", "luxury", "budget"]
RoomType = Literal["single", "double", "twin", "triple", "family", "suite"]


class RoomCount(BaseModel):
    type: RoomType
    count: int = Field(ge=1, le=200)


class Evidence(BaseModel):
    field: str
    text: str


class ExtractedRequirements(BaseModel):
    """Requirements found in the text. Every field is optional; place names are as written."""

    adults: int | None = Field(default=None, description="Number of adults")
    children: int | None = Field(default=None, description="Number of children (under 18)")
    children_ages: list[int] = Field(default_factory=list)
    arrival_date: date | None = None
    departure_date: date | None = None
    arrival_place: str | None = Field(default=None, description="Arrival city or airport as written")
    departure_place: str | None = Field(default=None, description="Departure city or airport as written")
    countries: list[str] = Field(default_factory=list, description="Countries to visit, as written")
    cities: list[str] = Field(default_factory=list, description="Cities or places to visit, as written")
    hotel_categories: list[HotelCategory] = Field(default_factory=list)
    rooms: list[RoomCount] = Field(default_factory=list)
    food_preferences: list[Food] = Field(default_factory=list)
    meals: list[Literal["breakfast", "lunch", "dinner"]] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    transport_modes: list[Transport] = Field(default_factory=list)
    travel_type: Literal["FIT", "GIT"] | None = None
    travel_pace: Literal["relaxed", "balanced", "fast"] | None = None
    budget_per_person: float | None = None
    budget_total: float | None = None
    currency: str | None = Field(default=None, description="ISO 4217 code, e.g. EUR, INR, USD")
    special_requests: list[str] = Field(default_factory=list, description="Other requests worth noting, short phrases")
    evidence: list[Evidence] = Field(default_factory=list, description="Short quotes from the text supporting each field")


WORD_NUMBERS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
NUM = r"(\d{1,3}|" + "|".join(WORD_NUMBERS) + r")"
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
COUNTRY_ALIASES = {
    "holland": "Netherlands", "dutch": "Netherlands", "swiss": "Switzerland", "england": "United Kingdom", "uk": "United Kingdom",
    "britain": "United Kingdom", "great britain": "United Kingdom", "czechia": "Czech Republic", "czech": "Czech Republic",
}
REGION_ALIASES = {"benelux": ["Belgium", "Netherlands", "Luxembourg"], "scandinavia": ["Denmark", "Norway", "Sweden"]}
INTEREST_WORDS = [
    (r"castles?|histor(?:y|ic|ical)|monuments?|heritage|landmarks?|palaces?", "historical_landmarks"),
    (r"museums?|art galler(?:y|ies)|\bart\b", "museums"),
    (r"mountains?|alps|alpine|snow|glaciers?|titlis|jungfrau(?:joch)?|matterhorn", "mountains"),
    (r"lakes?|lakeside", "lakes"),
    (r"scenic|views?|countryside|landscapes?|villages?", "scenic"),
    (r"shopping|shop\b|outlets?", "shopping"),
    (r"adventure|paragliding|rafting|hiking|zip.?line", "adventure"),
    (r"theme parks?|disneyland|europa.?park|amusement", "theme_parks"),
    (r"cultur(?:e|al)|local life|traditions?", "cultural"),
    (r"photo(?:graphy|s)?|instagram", "photography"),
    (r"relax(?:ed|ing)?|leisure|free time|unwind", "leisure"),
    (r"kids?\b|children|family", "family"),
    (r"nature|gardens?|parks?\b|tulips?|keukenhof|forests?|waterfalls?|falls\b", "nature"),
]
SPECIAL_WORDS = r"wheelchair|mobility|senior|elderly|honeymoon|anniversary|birthday|celebration|visa|insurance|allerg\w*|baby|infant|pram|stroller"


def _num(token: str) -> int | None:
    token = token.lower()
    if token.isdigit():
        return int(token)
    return WORD_NUMBERS.get(token)


def _amount(token: str) -> float:
    """3,000 / 3.000 / 3000 / 2,50,000 (Indian grouping) / 2999.50 -> number."""
    if "," in token and "." in token:
        return float(token.replace(",", ""))
    if "," in token:
        return float(token.replace(",", ""))
    if token.count(".") > 1 or re.fullmatch(r"\d{1,3}\.\d{3}", token):
        return float(token.replace(".", ""))
    return float(token)


def _snippet(text: str, m: re.Match, pad: int = 30) -> str:
    start, end = max(0, m.start() - pad), min(len(text), m.end() + pad)
    s = " ".join(text[start:end].split())
    return ("…" if start else "") + s + ("…" if end < len(text) else "")


def _future(d: date, today: date) -> date:
    return d if d >= today else d.replace(year=d.year + 1)


def _parse_dates(text: str, today: date) -> list[tuple[date, re.Match]]:
    found: list[tuple[date, re.Match]] = []
    low = text.lower()
    # 1 June 2027 / 1st June / 1-15 June 2027 / 1 to 15 June
    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*(?:-|–|to|until|till)\s*(\d{{1,2}})(?:st|nd|rd|th)?)?\s+(?:of\s+)?{MONTH_RE}\.?,?(?:\s+(\d{{4}}))?", low):
        month = MONTHS[m.group(3)[:3]]
        year = int(m.group(4)) if m.group(4) else today.year
        try:
            first = date(year, month, int(m.group(1)))
            found.append((first if m.group(4) else _future(first, today), m))
            if m.group(2):
                second = date(first.year, month, int(m.group(2)))
                found.append((second, m))
        except ValueError:
            continue
    # June 1, 2027 / June 1-15
    for m in re.finditer(rf"\b{MONTH_RE}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*(?:-|–|to)\s*(\d{{1,2}})(?:st|nd|rd|th)?)?(?:,?\s+(\d{{4}}))?\b", low):
        month = MONTHS[m.group(1)[:3]]
        year = int(m.group(4)) if m.group(4) else today.year
        try:
            first = date(year, month, int(m.group(2)))
            found.append((first if m.group(4) else _future(first, today), m))
            if m.group(3):
                found.append((date(first.year, month, int(m.group(3))), m))
        except ValueError:
            continue
    # 2027-06-01 and 01/06/2027 or 01.06.2027 (day first, as used in Europe and India)
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", low):
        try:
            found.append((date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m))
        except ValueError:
            pass
    for m in re.finditer(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", low):
        try:
            found.append((date(int(m.group(3)), int(m.group(2)), int(m.group(1))), m))
        except ValueError:
            pass
    return found


def extract(text: str, *, today: date, known_countries: list[str], known_cities: list[str]) -> ExtractedRequirements:
    r = ExtractedRequirements()
    ev = r.evidence
    low = text.lower()

    def note(field: str, m: re.Match) -> None:
        if not any(e.field == field for e in ev):
            ev.append(Evidence(field=field, text=_snippet(text, m)))

    # ---------------------------------------------------------------- travellers
    if m := re.search(rf"\b{NUM}\s+(?:adults?|grown.?ups?)\b", low):
        r.adults = _num(m.group(1)); note("adults", m)
    if m := re.search(rf"\b{NUM}\s+(?:children|child|kids?)\b", low):
        r.children = _num(m.group(1)); note("children", m)
    if m := re.search(r"\b(?:aged?|ages?)\s+((?:\d{1,2}(?:\s*(?:,|and|&|/)\s*)?)+)", low):
        r.children_ages = [int(x) for x in re.findall(r"\d{1,2}", m.group(1)) if int(x) < 18]
        if r.children_ages:
            note("children_ages", m)
            if r.children is None:
                r.children = len(r.children_ages)
    group = re.search(rf"\b(?:group|party) of\s+{NUM}\b", low)
    total = group or re.search(rf"\b(?:family of|total of)\s+{NUM}\b", low) or re.search(rf"\b{NUM}\s+(?:pax|people|persons|travell?ers|guests|passengers)\b", low)
    if total and r.adults is None:
        n = _num(total.group(1))
        if n:
            r.adults = max(n - (r.children or 0), 0)  # a total ("family of 6") includes the children
            note("adults", total)
    if re.search(r"\bgit\b", low) or group:
        r.travel_type = "GIT"
        if m := (group or re.search(r"\bgit\b", low)):
            note("travel_type", m)
    elif m := re.search(r"\bfit\b|\bindependent travel", low):
        r.travel_type = "FIT"; note("travel_type", m)

    # ---------------------------------------------------------------- dates
    dates = sorted({d: m for d, m in _parse_dates(text, today)}.items())
    if dates:
        r.arrival_date = dates[0][0]; note("arrival_date", dates[0][1])
        if len(dates) > 1:
            r.departure_date = dates[-1][0]; note("departure_date", dates[-1][1])
    length = re.search(rf"\b{NUM}\s*(?:days?|d)\b(?:\s*(?:/|and|,)?\s*{NUM}\s*(?:nights?|n)\b)?", low) or re.search(rf"\b{NUM}\s*(?:nights?|n)\b", low)
    if length and r.arrival_date and not r.departure_date:
        n = _num(length.group(1)) or 0
        nights = n if re.search(r"nights?|n\b", length.group(0)) and "day" not in length.group(0) else n - 1
        if 0 < nights < 60:
            r.departure_date = r.arrival_date + timedelta(days=nights)
            note("departure_date", length)

    # ---------------------------------------------------------------- places
    def find_names(names: list[str]) -> list[tuple[str, re.Match]]:
        out = []
        for name in sorted(names, key=len, reverse=True):
            m = re.search(rf"(?<![\w-]){re.escape(name.lower())}(?![\w-])", low)
            if m and not any(name.lower() in o.lower() for o, _ in out):
                out.append((name, m))
        return sorted(out, key=lambda x: x[1].start())

    for name, m in find_names(known_countries):
        r.countries.append(name); note("countries", m)
    for alias, country in COUNTRY_ALIASES.items():
        if (m := re.search(rf"\b{alias}\b", low)) and country not in r.countries:
            r.countries.append(country); note("countries", m)
    for region, members in REGION_ALIASES.items():
        if m := re.search(rf"\b{region}\b", low):
            r.countries.extend(c for c in members if c not in r.countries); note("countries", m)
    for name, m in find_names(known_cities):
        if name not in r.countries:
            r.cities.append(name); note("cities", m)

    # Places in "must see / visit / cover ..." lists that are not in inventory: reported, so the planner sees them.
    known_lower = {n.lower() for n in known_countries + known_cities + r.countries + r.cities} | set(COUNTRY_ALIASES) | set(REGION_ALIASES)
    for m in re.finditer(r"(?i:must (?:see|visit|cover|include)|visit(?:ing)?|cover(?:ing)?|including|see)\s+([^.\n;:!?]+)", text):
        for part in re.split(r",|\band\b|&|\bor\b|\bplus\b", m.group(1)):
            part = re.sub(r"^(?:the|ideally|also|maybe|possibly)\s+", "", part.strip(), flags=re.I)
            if re.fullmatch(r"[A-Z][\w'’-]+(?: [A-Z][\w'’-]+)?", part) and part.lower() not in known_lower:
                r.cities.append(part)
                known_lower.add(part.lower())

    place = r"([A-Z][\w'’-]+(?:[ ][A-Z][\w'’-]+)?)"  # one or two capitalised words, stops at punctuation
    if m := re.search(rf"(?i:arriv\w*|land\w*|fly\w* into|start\w*|begin\w*)\s+(?i:in|at|into|from)?\s*{place}", text):
        r.arrival_place = m.group(1).strip(); note("arrival_place", m)
    if m := re.search(rf"(?i:depart\w*|fly\w* (?:out|back)|leav\w*|end\w*|return\w*|exit\w*)\s+(?i:from|in|at|out of|of|via)?\s*{place}", text):
        r.departure_place = m.group(1).strip(); note("departure_place", m)

    # ---------------------------------------------------------------- hotels and rooms
    for m in re.finditer(r"\b([345])\s*(?:\*|-?\s*stars?|★)", low):
        cat = f"{m.group(1)}_star"
        if cat not in r.hotel_categories:
            r.hotel_categories.append(cat); note("hotel_categories", m)
    for word, cat in (("boutique", "boutique"), ("luxury", "luxury"), ("budget hotel", "budget")):
        if (m := re.search(rf"\b{word}\b", low)) and cat not in r.hotel_categories:
            r.hotel_categories.append(cat); note("hotel_categories", m)
    for m in re.finditer(rf"\b{NUM}\s+(single|double|twin|triple|family|suite)s?(?:\s+rooms?)?\b", low):
        n = _num(m.group(1))
        if n:
            r.rooms.append(RoomCount(type=m.group(2), count=n)); note("rooms", m)

    # ---------------------------------------------------------------- food and meals
    food_rules = [
        (r"\bjain\b", "indian_jain"), (r"non[\s-]?veg(?:etarian)?", "indian_non_vegetarian"), (r"\bhalal\b", "halal"),
        (r"\bvegan\b", "vegan"), (r"(?<!non[\s-])(?<!non)\bveg(?:etarian)?\b|pure veg", "indian_vegetarian"),
        (r"continental", "continental"),
    ]
    for pattern, value in food_rules:
        if (m := re.search(pattern, low)) and value not in r.food_preferences:
            r.food_preferences.append(value); note("food_preferences", m)
    if m := re.search(r"all meals|full board|three meals|breakfast,? lunch,? (?:and|&) dinner", low):
        r.meals = ["breakfast", "lunch", "dinner"]; note("meals", m)
    elif m := re.search(r"half board|map plan", low):
        r.meals = ["breakfast", "dinner"]; note("meals", m)
    else:
        for meal in ("breakfast", "lunch", "dinner"):
            if m := re.search(rf"\b{meal}s?\b", low):
                r.meals.append(meal); note("meals", m)

    # ---------------------------------------------------------------- interests, pace, transport
    for pattern, tag in INTEREST_WORDS:
        if (m := re.search(rf"\b(?:{pattern})", low)) and tag not in r.interests:
            r.interests.append(tag); note("interests", m)
    if m := re.search(r"relaxed|leisurely|slow pace|not too rushed|easy pace", low):
        r.travel_pace = "relaxed"; note("travel_pace", m)
    elif m := re.search(r"fast[\s-]paced|packed|cover (?:as much|maximum)|whirlwind", low):
        r.travel_pace = "fast"; note("travel_pace", m)
    transport_rules = [
        (r"luxury coach", "luxury_coach"), (r"mini[\s-]?bus|sprinter|tempo traveller", "mini_bus"),
        (r"(?<!mini )(?<!mini-)\b(?:coach|bus)\b", "private_coach"), (r"private car|sedan|\bcar\b|\bvan\b", "private_car"),
        (r"\btrains?\b|\brail\b|eurostar|tgv", "train"),
    ]
    for pattern, mode in transport_rules:
        if (m := re.search(pattern, low)) and mode not in r.transport_modes:
            if mode == "private_coach" and "luxury_coach" in r.transport_modes:
                continue
            r.transport_modes.append(mode); note("transport_modes", m)

    # ---------------------------------------------------------------- budget
    cur = r"(€|eur(?:os?)?|inr|rs\.?|₹|usd|us\$|\$|£|gbp|chf)"
    # 2,50,000 (Indian grouping) | 3,000 / 3.000 | 2999.50
    amount = r"(\d{1,3}(?:,\d{2})+,\d{3}|\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)\s*(k|lakhs?|lacs?)?"
    m = re.search(rf"{cur}\s*{amount}", low) or re.search(rf"{amount}\s*{cur}", low)
    if m:
        groups = m.groups()
        currency_token = groups[0] if re.match(cur, groups[0] or "") else groups[-1]
        num_token = groups[1] if currency_token == groups[0] else groups[0]
        mult = groups[2] if currency_token == groups[0] else groups[1]
        value = _amount(num_token)
        if mult:
            value *= 1000 if mult.startswith("k") else 100000
        code = {"€": "EUR", "eur": "EUR", "euro": "EUR", "euros": "EUR", "inr": "INR", "rs": "INR", "rs.": "INR", "₹": "INR",
                "usd": "USD", "us$": "USD", "$": "USD", "£": "GBP", "gbp": "GBP", "chf": "CHF"}.get(currency_token.strip(), None)
        r.currency = code
        tail = low[m.end(): m.end() + 30]
        head = low[max(0, m.start() - 25): m.start()]
        if re.search(r"\b(pp|p\.p\.|per (?:person|head|pax|adult)|each|/person|/pax)\b", tail + " " + head):
            r.budget_per_person = value; note("budget_per_person", m)
        else:
            r.budget_total = value; note("budget_total", m)

    # ---------------------------------------------------------------- special requests
    for m in re.finditer(rf"[^.!?\n]*\b(?:{SPECIAL_WORDS})[^.!?\n]*", text, flags=re.I):
        phrase = " ".join(m.group(0).split())[:200]
        if phrase and phrase not in r.special_requests:
            r.special_requests.append(phrase)
    return r
