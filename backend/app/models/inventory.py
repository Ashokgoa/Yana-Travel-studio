"""Destination inventory (PRD Parts 8–11): countries, cities, suppliers,
attractions, hotels (+ room types, seasonal rates), restaurants, vehicles.

Conventions:
- Soft delete via `is_active`; itineraries will reference these rows.
- `is_demo` marks fictional demonstration records (PRD Part 21).
- Prices carry `price_is_verified`; unverified prices are shown as "Estimated".
- Restaurant dietary flags are nullable: NULL = unknown, never assumed (PRD Part 10).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin

Money = Numeric(12, 2)


class Country(IdMixin, TimestampMixin, Base):
    __tablename__ = "countries"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    iso_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    cities: Mapped[list["City"]] = relationship(back_populates="country", order_by="City.name")


class City(IdMixin, TimestampMixin, Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("country_id", "name", name="uq_cities_country_id_name"),)

    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    recommended_nights_min: Mapped[int | None] = mapped_column(Integer)
    recommended_nights_max: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    country: Mapped[Country] = relationship(back_populates="cities")


class Supplier(IdMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    supplier_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    country_id: Mapped[int | None] = mapped_column(ForeignKey("countries.id", ondelete="SET NULL"), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    country: Mapped[Country | None] = relationship()


class Attraction(IdMixin, TimestampMixin, Base):
    __tablename__ = "attractions"

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    interest_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    recommended_duration_min: Mapped[int | None] = mapped_column(Integer)
    opening_hours: Mapped[str | None] = mapped_column(String(500))
    operating_days: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)  # ["mon", ...]
    ticket_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ticket_price: Mapped[Decimal | None] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    price_is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    seasonal_info: Mapped[str | None] = mapped_column(String(500))
    child_friendly: Mapped[bool | None] = mapped_column(Boolean)
    setting: Mapped[str | None] = mapped_column(String(20))  # indoor / outdoor / mixed
    address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    city: Mapped[City] = relationship()
    supplier: Mapped[Supplier | None] = relationship()


class Hotel(IdMixin, TimestampMixin, Base):
    __tablename__ = "hotels"

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    star_rating: Mapped[int | None] = mapped_column(Integer, index=True)
    style_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    location_type: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    breakfast_available: Mapped[bool | None] = mapped_column(Boolean)
    facilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    parking: Mapped[bool | None] = mapped_column(Boolean)
    group_capacity_rooms: Mapped[int | None] = mapped_column(Integer)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    city: Mapped[City] = relationship()
    supplier: Mapped[Supplier | None] = relationship()
    room_types: Mapped[list["HotelRoomType"]] = relationship(
        back_populates="hotel", cascade="all, delete-orphan", order_by="HotelRoomType.id"
    )
    rates: Mapped[list["HotelRate"]] = relationship(
        back_populates="hotel", cascade="all, delete-orphan", order_by="HotelRate.valid_from"
    )


class HotelRoomType(IdMixin, TimestampMixin, Base):
    __tablename__ = "hotel_room_types"

    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_occupancy: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    bed_config: Mapped[str | None] = mapped_column(String(100))
    base_price: Mapped[Decimal | None] = mapped_column(Money)  # per room per night
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    price_is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    hotel: Mapped[Hotel] = relationship(back_populates="room_types")


class HotelRate(IdMixin, TimestampMixin, Base):
    """Seasonal price for a room type (per room per night) over a date range."""

    __tablename__ = "hotel_rates"

    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("hotel_room_types.id", ondelete="CASCADE"), nullable=False, index=True)
    season_name: Mapped[str] = mapped_column(String(100), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    hotel: Mapped[Hotel] = relationship(back_populates="rates")
    room_type: Mapped[HotelRoomType] = relationship()


class Restaurant(IdMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cuisine: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    # Dietary availability: True = verified available, False = verified not available, NULL = unknown.
    vegetarian: Mapped[bool | None] = mapped_column(Boolean)
    jain: Mapped[bool | None] = mapped_column(Boolean)
    halal: Mapped[bool | None] = mapped_column(Boolean)
    vegan: Mapped[bool | None] = mapped_column(Boolean)
    non_vegetarian: Mapped[bool | None] = mapped_column(Boolean)
    group_capacity: Mapped[int | None] = mapped_column(Integer)
    price_range: Mapped[str | None] = mapped_column(String(10))  # €, €€, €€€
    avg_price_per_person: Mapped[Decimal | None] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    price_is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opening_hours: Mapped[str | None] = mapped_column(String(500))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    city: Mapped[City] = relationship()
    supplier: Mapped[Supplier | None] = relationship()


class VehicleCategory(IdMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_categories"

    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    passenger_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    luggage_capacity: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


vehicle_countries = Table(
    "vehicle_countries",
    Base.metadata,
    Column("vehicle_id", ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True),
    Column("country_id", ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True),
)


class Vehicle(IdMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    category_id: Mapped[int] = mapped_column(ForeignKey("vehicle_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    passenger_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    luggage_capacity: Mapped[int | None] = mapped_column(Integer)
    service_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    price_per_day: Mapped[Decimal | None] = mapped_column(Money)
    price_per_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    driver_cost_per_day: Mapped[Decimal | None] = mapped_column(Money)
    additional_costs: Mapped[str | None] = mapped_column(String(1000))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    price_is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    availability_notes: Mapped[str | None] = mapped_column(String(1000))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    category: Mapped[VehicleCategory] = relationship()
    supplier: Mapped[Supplier | None] = relationship()
    operating_countries: Mapped[list[Country]] = relationship(secondary=vehicle_countries, order_by="Country.name")
