"""Customer requirement capture (PRD Part 7) – vocabularies, input and output schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import CurrencyCode, OptStr, ORMModel
from app.schemas.inventory import INTEREST_TAGS, CityRef, CountryRef

PREFERENCES = ["mandatory", "preferred", "optional", "avoid"]
HOTEL_CATEGORIES = ["3_star", "4_star", "5_star", "boutique", "luxury", "budget"]
HOTEL_LOCATIONS = ["city_centre", "airport", "anywhere"]
ROOM_TYPES = ["single", "double", "twin", "triple", "family", "suite"]
FOOD_PREFERENCES = ["indian_vegetarian", "indian_jain", "indian_non_vegetarian", "halal", "vegan", "continental", "mixed"]
MEALS = ["breakfast", "lunch", "dinner"]
TRANSPORT_MODES = ["private_coach", "luxury_coach", "mini_bus", "private_car", "train", "mixed"]
TRAVEL_PACES = ["relaxed", "balanced", "fast"]
BUDGET_FLEX = ["strict", "some", "flexible"]
TRAVEL_CLASSES = ["budget", "standard", "premium", "luxury"]
TOTAL_STEPS = 9


def _vocab(values: list[str], allowed: list[str], label: str) -> list[str]:
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown {label}: {', '.join(unknown)}")
    return list(dict.fromkeys(values))


class RoomLine(BaseModel):
    type: str
    count: int = Field(ge=1, le=200)

    @field_validator("type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in ROOM_TYPES:
            raise ValueError(f"Unknown room type: {v}")
        return v


class DestinationIn(BaseModel):
    country_id: int
    city_id: int | None = None
    preference: Literal["mandatory", "preferred", "optional", "avoid"]
    min_nights: int | None = Field(default=None, ge=1, le=30)


class DestinationOut(ORMModel):
    id: int
    country: CountryRef
    city: CityRef | None
    preference: str
    min_nights: int | None
    sort_order: int


class RequirementIn(BaseModel):
    """Saved as a draft at every step; completeness is reported, not enforced."""

    # Step 1
    adults: int = Field(default=1, ge=0, le=500)
    children: int = Field(default=0, ge=0, le=500)
    children_ages: list[int] = Field(default_factory=list)
    # Step 2
    arrival_date: date | None = None
    departure_date: date | None = None
    arrival_airport: OptStr = Field(default=None, max_length=100)
    departure_airport: OptStr = Field(default=None, max_length=100)
    start_country_id: int | None = None
    end_country_id: int | None = None
    travel_type: Literal["FIT", "GIT"] | None = None
    group_size: int | None = Field(default=None, ge=1, le=1000)
    # Step 3
    destinations: list[DestinationIn] = Field(default_factory=list, max_length=60)
    # Step 4
    interests: list[str] = Field(default_factory=list)
    travel_pace: Literal["relaxed", "balanced", "fast"] | None = None
    # Step 5
    hotel_categories: list[str] = Field(default_factory=list)
    hotel_locations: list[str] = Field(default_factory=list)
    breakfast_required: bool = True
    rooms: list[RoomLine] = Field(default_factory=list)
    # Step 6
    food_preferences: list[str] = Field(default_factory=list)
    meals: list[str] = Field(default_factory=list)
    # Step 7
    transport_modes: list[str] = Field(default_factory=list)
    passenger_capacity: int | None = Field(default=None, ge=1, le=1000)
    luggage_notes: OptStr = Field(default=None, max_length=500)
    airport_transfers: bool = True
    local_sightseeing_transport: bool = True
    # Step 8
    budget_per_person: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_total: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: CurrencyCode = "EUR"
    budget_flexibility: Literal["strict", "some", "flexible"] | None = None
    travel_class: Literal["budget", "standard", "premium", "luxury"] | None = None
    # Step 9
    additional_requirements: OptStr = Field(default=None, max_length=5000)
    internal_notes: OptStr = Field(default=None, max_length=5000)

    completed_steps: list[int] = Field(default_factory=list)

    @field_validator("interests")
    @classmethod
    def _interests(cls, v):
        return _vocab(v, INTEREST_TAGS, "interests")

    @field_validator("hotel_categories")
    @classmethod
    def _hotel_categories(cls, v):
        return _vocab(v, HOTEL_CATEGORIES, "hotel categories")

    @field_validator("hotel_locations")
    @classmethod
    def _hotel_locations(cls, v):
        return _vocab(v, HOTEL_LOCATIONS, "hotel locations")

    @field_validator("food_preferences")
    @classmethod
    def _food(cls, v):
        return _vocab(v, FOOD_PREFERENCES, "food preferences")

    @field_validator("meals")
    @classmethod
    def _meals(cls, v):
        return sorted(_vocab(v, MEALS, "meals"), key=MEALS.index)

    @field_validator("transport_modes")
    @classmethod
    def _transport(cls, v):
        return _vocab(v, TRANSPORT_MODES, "transport modes")

    @field_validator("completed_steps")
    @classmethod
    def _steps(cls, v):
        return sorted({s for s in v if 1 <= s <= TOTAL_STEPS})

    @model_validator(mode="after")
    def _consistency(self):
        if self.adults + self.children < 1:
            raise ValueError("At least one traveller is required.")
        if len(self.children_ages) != self.children:
            raise ValueError(f"Provide an age for each child ({self.children} expected, {len(self.children_ages)} given).")
        if any(a < 0 or a > 17 for a in self.children_ages):
            raise ValueError("Children's ages must be between 0 and 17.")
        if self.arrival_date and self.departure_date and self.departure_date < self.arrival_date:
            raise ValueError("Departure date cannot be before the arrival date.")
        keys = [(d.country_id, d.city_id) for d in self.destinations]
        if len(keys) != len(set(keys)):
            raise ValueError("Each country/city can only be listed once in destinations.")
        return self


class RequirementOut(ORMModel):
    enquiry_id: int
    exists: bool = True
    adults: int
    children: int
    children_ages: list[int]
    arrival_date: date | None
    departure_date: date | None
    arrival_airport: str | None
    departure_airport: str | None
    start_country_id: int | None
    end_country_id: int | None
    travel_type: str | None
    group_size: int | None
    destinations: list[DestinationOut]
    interests: list[str]
    travel_pace: str | None
    hotel_categories: list[str]
    hotel_locations: list[str]
    breakfast_required: bool
    rooms: list[RoomLine]
    food_preferences: list[str]
    meals: list[str]
    transport_modes: list[str]
    passenger_capacity: int | None
    luggage_notes: str | None
    airport_transfers: bool
    local_sightseeing_transport: bool
    budget_per_person: Decimal | None
    budget_total: Decimal | None
    currency: str
    budget_flexibility: str | None
    travel_class: str | None
    additional_requirements: str | None
    internal_notes: str | None
    completed_steps: list[int]
    updated_at: datetime | None = None
    # computed
    total_days: int | None = None
    total_nights: int | None = None
    total_travellers: int = 0
    rooms_count: int = 0
    room_capacity: int = 0
    missing: list[str] = []
    warnings: list[str] = []
    is_complete: bool = False


class RequirementOptions(BaseModel):
    preferences: list[str] = PREFERENCES
    interests: list[str] = INTEREST_TAGS
    hotel_categories: list[str] = HOTEL_CATEGORIES
    hotel_locations: list[str] = HOTEL_LOCATIONS
    room_types: list[str] = ROOM_TYPES
    food_preferences: list[str] = FOOD_PREFERENCES
    meals: list[str] = MEALS
    transport_modes: list[str] = TRANSPORT_MODES
    travel_paces: list[str] = TRAVEL_PACES
    budget_flexibility: list[str] = BUDGET_FLEX
    travel_classes: list[str] = TRAVEL_CLASSES
