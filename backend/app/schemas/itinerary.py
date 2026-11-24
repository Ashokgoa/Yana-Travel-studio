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
