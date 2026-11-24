from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Strategy = Literal["classic", "scenic", "premium"]


class GenerateRequest(BaseModel):
    strategies: list[Strategy] = Field(default_factory=lambda: ["classic", "scenic", "premium"], min_length=1)


class RouteStop(BaseModel):
    city_id: int
    city: str
    country: str
    iso_code: str
    nights: int
    lat: float | None = None
    lng: float | None = None


class HotelRef(BaseModel):
    id: int
    name: str
    stars: int | None
    is_demo: bool
    image_url: str | None = None


class CostLineOut(BaseModel):
    category: str
    description: str
    amount: str | None
    currency: str
    is_estimate: bool


class ItinerarySummary(BaseModel):
    id: int
    enquiry_id: int | None
    enquiry_reference: str | None = None
    customer_name: str | None = None
    title: str
    strategy: str
    strategy_summary: str
    status: str
    batch: int
    created_at: datetime
    version_number: int
    version_label: str
    version_notes: str | None = None
    is_locked: bool = True
    latest_version_number: int = 1
    start_date: date
    total_days: int
    total_nights: int
    route: list[RouteStop]
    hotels: list[HotelRef | None]
    total_cost: str | None
    cost_per_person: str | None
    currency: str
    unknown_cost_items: int
    total_distance_km: int
    warnings_count: int


class ActivityOut(BaseModel):
    id: int
    time_slot: str
    activity_type: str
    title: str
    description: str | None
    duration_min: int | None
    attraction_id: int | None
    image_url: str | None = None


class MealOut(BaseModel):
    id: int
    meal: str
    arrangement: str
    restaurant_id: int | None
    restaurant_name: str | None = None
    cuisine: str | None = None
    note: str | None


class DayOut(BaseModel):
    id: int
    day_number: int
    date: date
    city_id: int
    city: str
    overnight_city: str | None
    title: str
    description: str | None
    activities: list[ActivityOut]
    meals: list[MealOut]


class StayOut(BaseModel):
    id: int
    city_id: int
    city: str
    check_in_day: int
    nights: int
    hotel: HotelRef | None
    rooms: list[dict]
    alternatives: list[HotelRef]
    estimated_cost: str | None
    note: str | None


class TransportOut(BaseModel):
    id: int
    day_number: int
    kind: str
    mode: str
    from_city: str | None
    to_city: str | None
    vehicle: str | None
    distance_km: int | None
    duration_min: int | None
    is_estimate: bool
    note: str | None


class ItineraryDetail(ItinerarySummary):
    explanations: list[str]
    warnings: list[str]
    costs: list[CostLineOut]
    vehicle: str | None
    days: list[DayOut]
    stays: list[StayOut]
    transports: list[TransportOut]


class VersionInfo(BaseModel):
    version_number: int
    label: str
    notes: str | None
    is_locked: bool
    created_at: datetime
    created_by: str | None
    total_days: int
    total_nights: int
    total_cost: str | None
    currency: str


class SaveVersionRequest(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class DayUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


TimeSlot = Literal["morning", "afternoon", "full_day", "evening"]


class ActivityCreate(BaseModel):
    time_slot: TimeSlot
    attraction_id: int | None = None
    activity_type: Literal["free_time", "custom", "transfer"] = "custom"
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    duration_min: int | None = Field(default=None, ge=0, le=24 * 60)


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    time_slot: TimeSlot | None = None
    duration_min: int | None = Field(default=None, ge=0, le=24 * 60)


class ActivityMove(BaseModel):
    day_number: int = Field(ge=1)
    position: int = Field(ge=0)
    time_slot: TimeSlot | None = None


class MealUpdate(BaseModel):
    arrangement: Literal["hotel", "restaurant", "own", "none"]
    restaurant_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class HotelReplace(BaseModel):
    hotel_id: int


class VehicleUpdate(BaseModel):
    vehicle_id: int | None


class LegModeUpdate(BaseModel):
    mode: Literal["coach", "minibus", "car", "train"]


class VersionDiff(BaseModel):
    a: int
    b: int
    summary: list[str]
    route_a: list[str]
    route_b: list[str]
    cost_a: str | None
    cost_b: str | None
    currency: str
