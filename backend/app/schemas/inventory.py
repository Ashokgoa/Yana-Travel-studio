"""Inventory request/response schemas.

Input schemas validate business rules (ranges, enums, coordinates). Output
schemas embed small references (city → country, supplier) so lists render
without extra requests.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import CurrencyCode, OptEmail, OptStr, ORMModel, RequiredStr


class SupplierType(StrEnum):
    HOTEL = "hotel"
    COACH = "coach"
    RESTAURANT = "restaurant"
    GUIDE = "guide"
    ATTRACTION = "attraction"
    OTHER = "other"


class AttractionSetting(StrEnum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    MIXED = "mixed"


class LocationType(StrEnum):
    CITY_CENTRE = "city_centre"
    AIRPORT = "airport"
    SUBURBAN = "suburban"
    RESORT = "resort"


class ServiceType(StrEnum):
    AIRPORT_TRANSFER = "airport_transfer"
    LOCAL = "local"
    INTERCITY = "intercity"
    LONG_DISTANCE = "long_distance"


# Vocabularies shared with the frontend and (later) the itinerary engine.
ATTRACTION_CATEGORIES = [
    "landmark", "museum", "nature", "mountain", "lake", "scenic", "shopping", "adventure",
    "theme_park", "cultural", "family", "leisure", "tour", "other",
]
INTEREST_TAGS = [
    "historical_landmarks", "nature", "mountains", "lakes", "scenic", "museums", "shopping", "adventure",
    "theme_parks", "cultural", "photography", "leisure", "family",
]
HOTEL_STYLES = ["boutique", "luxury", "budget", "business", "family", "resort"]
HOTEL_FACILITIES = [
    "wifi", "restaurant", "bar", "gym", "spa", "pool", "family_rooms", "accessible_rooms",
    "air_conditioning", "airport_shuttle", "coach_parking", "meeting_rooms", "room_service", "lift",
]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
PRICE_RANGES = ["€", "€€", "€€€", "€€€€"]

Latitude = Annotated[float | None, Field(default=None, ge=-90, le=90)]
Longitude = Annotated[float | None, Field(default=None, ge=-180, le=180)]
Price = Annotated[Decimal | None, Field(default=None, ge=0, max_digits=12, decimal_places=2)]


def _check_vocab(values: list[str], allowed: list[str], label: str) -> list[str]:
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown {label}: {', '.join(unknown)}")
    return list(dict.fromkeys(values))  # de-duplicate, keep order


# ------------------------------------------------------------------ refs
class CountryRef(ORMModel):
    id: int
    name: str
    iso_code: str


class CityRef(ORMModel):
    id: int
    name: str
    country: CountryRef


class SupplierRef(ORMModel):
    id: int
    name: str
    supplier_type: str


class InventoryOutBase(ORMModel):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    primary_image_url: str | None = None


# ------------------------------------------------------------------ countries
class CountryIn(BaseModel):
    name: RequiredStr = Field(max_length=100)
    iso_code: str = Field(pattern=r"^[A-Za-z]{2}$", description="ISO 3166-1 alpha-2, e.g. NL")
    region: OptStr = Field(default=None, max_length=100)
    description: OptStr = None
    sort_order: int = 0
    is_active: bool = True

    @field_validator("iso_code")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class CountryOut(CountryIn, InventoryOutBase):
    city_count: int = 0


# ------------------------------------------------------------------ cities
class CityIn(BaseModel):
    country_id: int
    name: RequiredStr = Field(max_length=100)
    description: OptStr = None
    latitude: Latitude = None
    longitude: Longitude = None
    recommended_nights_min: int | None = Field(default=None, ge=0, le=30)
    recommended_nights_max: int | None = Field(default=None, ge=0, le=30)
    is_active: bool = True

    @model_validator(mode="after")
    def _check(self):
        lo, hi = self.recommended_nights_min, self.recommended_nights_max
        if lo is not None and hi is not None and hi < lo:
            raise ValueError("Recommended maximum nights cannot be less than the minimum.")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Enter both latitude and longitude, or neither.")
        return self


class CityOut(CityIn, InventoryOutBase):
    country: CountryRef


# ------------------------------------------------------------------ suppliers
class SupplierIn(BaseModel):
    name: RequiredStr = Field(max_length=200)
    supplier_type: SupplierType
    contact_name: OptStr = Field(default=None, max_length=200)
    email: OptEmail = None
    phone: OptStr = Field(default=None, max_length=50)
    country_id: int | None = None
    address: OptStr = Field(default=None, max_length=500)
    notes: OptStr = None
    is_demo: bool = False
    is_active: bool = True


class SupplierOut(SupplierIn, InventoryOutBase):
    country: CountryRef | None


# ------------------------------------------------------------------ attractions
class AttractionIn(BaseModel):
    city_id: int
    name: RequiredStr = Field(max_length=200)
    category: str
    interest_tags: list[str] = Field(default_factory=list)
    description: OptStr = None
    recommended_duration_min: int | None = Field(default=None, ge=0, le=24 * 60)
    opening_hours: OptStr = Field(default=None, max_length=500)
    operating_days: list[str] = Field(default_factory=list)
    ticket_required: bool = False
    ticket_price: Price = None
    currency: CurrencyCode = "EUR"
    price_is_verified: bool = False
    seasonal_info: OptStr = Field(default=None, max_length=500)
    child_friendly: bool | None = None
    setting: AttractionSetting | None = None
    address: OptStr = Field(default=None, max_length=500)
    latitude: Latitude = None
    longitude: Longitude = None
    supplier_id: int | None = None
    is_demo: bool = False
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def _cat(cls, v: str) -> str:
        if v not in ATTRACTION_CATEGORIES:
            raise ValueError(f"Unknown category: {v}")
        return v

    @field_validator("interest_tags")
    @classmethod
    def _tags(cls, v: list[str]) -> list[str]:
        return _check_vocab(v, INTEREST_TAGS, "interest tags")

    @field_validator("operating_days")
    @classmethod
    def _days(cls, v: list[str]) -> list[str]:
        days = _check_vocab([d.lower() for d in v], WEEKDAYS, "weekdays")
        return sorted(days, key=WEEKDAYS.index)


class AttractionOut(AttractionIn, InventoryOutBase):
    city: CityRef
    supplier: SupplierRef | None


# ------------------------------------------------------------------ hotels
class HotelIn(BaseModel):
    city_id: int
    name: RequiredStr = Field(max_length=200)
    star_rating: int | None = Field(default=None, ge=1, le=5)
    style_tags: list[str] = Field(default_factory=list)
    location_type: LocationType | None = None
    description: OptStr = None
    address: OptStr = Field(default=None, max_length=500)
    latitude: Latitude = None
    longitude: Longitude = None
    breakfast_available: bool | None = None
    facilities: list[str] = Field(default_factory=list)
    parking: bool | None = None
    group_capacity_rooms: int | None = Field(default=None, ge=0, le=2000)
    supplier_id: int | None = None
    contact_email: OptEmail = None
    contact_phone: OptStr = Field(default=None, max_length=50)
    is_demo: bool = False
    is_active: bool = True

    @field_validator("style_tags")
    @classmethod
    def _styles(cls, v: list[str]) -> list[str]:
        return _check_vocab(v, HOTEL_STYLES, "hotel styles")

    @field_validator("facilities")
    @classmethod
    def _facilities(cls, v: list[str]) -> list[str]:
        return _check_vocab(v, HOTEL_FACILITIES, "facilities")


class RoomTypeIn(BaseModel):
    name: RequiredStr = Field(max_length=100)
    max_occupancy: int = Field(default=2, ge=1, le=12)
    bed_config: OptStr = Field(default=None, max_length=100)
    base_price: Price = None
    currency: CurrencyCode = "EUR"
    price_is_verified: bool = False


class RoomTypeOut(RoomTypeIn, ORMModel):
    id: int


class RateIn(BaseModel):
    room_type_id: int
    season_name: RequiredStr = Field(max_length=100)
    valid_from: date
    valid_to: date
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: CurrencyCode = "EUR"
    is_verified: bool = False

    @model_validator(mode="after")
    def _dates(self):
        if self.valid_to < self.valid_from:
            raise ValueError("'Valid to' cannot be before 'valid from'.")
        return self


class RateOut(RateIn, ORMModel):
    id: int


class HotelOut(HotelIn, InventoryOutBase):
    city: CityRef
    supplier: SupplierRef | None
    room_types: list[RoomTypeOut] = []
    rates: list[RateOut] = []


# ------------------------------------------------------------------ restaurants
class RestaurantIn(BaseModel):
    city_id: int
    name: RequiredStr = Field(max_length=200)
    cuisine: OptStr = Field(default=None, max_length=100)
    description: OptStr = None
    address: OptStr = Field(default=None, max_length=500)
    latitude: Latitude = None
    longitude: Longitude = None
    vegetarian: bool | None = None
    jain: bool | None = None
    halal: bool | None = None
    vegan: bool | None = None
    non_vegetarian: bool | None = None
    group_capacity: int | None = Field(default=None, ge=0, le=5000)
    price_range: str | None = None
    avg_price_per_person: Price = None
    currency: CurrencyCode = "EUR"
    price_is_verified: bool = False
    opening_hours: OptStr = Field(default=None, max_length=500)
    supplier_id: int | None = None
    contact_email: OptEmail = None
    contact_phone: OptStr = Field(default=None, max_length=50)
    is_demo: bool = False
    is_active: bool = True

    @field_validator("price_range")
    @classmethod
    def _range(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if v not in PRICE_RANGES:
            raise ValueError(f"Price range must be one of {', '.join(PRICE_RANGES)}")
        return v


class RestaurantOut(RestaurantIn, InventoryOutBase):
    city: CityRef
    supplier: SupplierRef | None


# ------------------------------------------------------------------ vehicles
class VehicleCategoryOut(ORMModel):
    id: int
    code: str
    name: str
    passenger_capacity: int
    luggage_capacity: int | None


class VehicleIn(BaseModel):
    category_id: int
    name: RequiredStr = Field(max_length=200)
    passenger_capacity: int = Field(ge=1, le=100)
    luggage_capacity: int | None = Field(default=None, ge=0, le=200)
    supplier_id: int | None = None
    service_types: list[ServiceType] = Field(default_factory=list)
    operating_country_ids: list[int] = Field(default_factory=list)
    price_per_day: Price = None
    price_per_km: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    driver_cost_per_day: Price = None
    additional_costs: OptStr = Field(default=None, max_length=1000)
    currency: CurrencyCode = "EUR"
    price_is_verified: bool = False
    availability_notes: OptStr = Field(default=None, max_length=1000)
    is_demo: bool = False
    is_active: bool = True


class VehicleOut(InventoryOutBase):
    category_id: int
    name: str
    passenger_capacity: int
    luggage_capacity: int | None
    supplier_id: int | None
    service_types: list[ServiceType]
    price_per_day: Decimal | None
    price_per_km: Decimal | None
    driver_cost_per_day: Decimal | None
    additional_costs: str | None
    currency: str
    price_is_verified: bool
    availability_notes: str | None
    is_demo: bool
    category: VehicleCategoryOut
    supplier: SupplierRef | None
    operating_countries: list[CountryRef]


class StatusBody(BaseModel):
    is_active: bool


class InventoryOptions(BaseModel):
    """Vocabularies for building forms and filters in the UI."""

    attraction_categories: list[str] = ATTRACTION_CATEGORIES
    interest_tags: list[str] = INTEREST_TAGS
    hotel_styles: list[str] = HOTEL_STYLES
    hotel_facilities: list[str] = HOTEL_FACILITIES
    weekdays: list[str] = WEEKDAYS
    price_ranges: list[str] = PRICE_RANGES
    supplier_types: list[str] = [t.value for t in SupplierType]
    location_types: list[str] = [t.value for t in LocationType]
    attraction_settings: list[str] = [t.value for t in AttractionSetting]
    service_types: list[str] = [t.value for t in ServiceType]
