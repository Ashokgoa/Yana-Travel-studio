"""Itineraries (PRD Parts 13-14). Every itinerary has versions; the content
(days, activities, stays, meals, transport) belongs to a version so earlier
versions are preserved when a planner edits (Phase 5).

Rows always REFERENCE inventory (hotel_id, attraction_id, restaurant_id,
vehicle_id); free-text titles/notes allow wording changes without copying records.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin


class Itinerary(IdMixin, TimestampMixin, Base):
    __tablename__ = "itineraries"

    enquiry_id: Mapped[int | None] = mapped_column(ForeignKey("enquiries.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="proposal", nullable=False)  # proposal / template
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False)  # classic / scenic / premium / custom
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    batch: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # generation run within the enquiry
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # PDF designer settings (schemas.proposal.ProposalSettings); NULL = defaults.
    proposal_settings: Mapped[dict | None] = mapped_column(JSON)

    versions: Mapped[list["ItineraryVersion"]] = relationship(
        back_populates="itinerary", cascade="all, delete-orphan", order_by="ItineraryVersion.version_number"
    )


class ItineraryVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_versions"
    __table_args__ = (UniqueConstraint("itinerary_id", "version_number", name="uq_itinerary_versions_number"),)

    itinerary_id: Mapped[int] = mapped_column(ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    total_nights: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    # Engine output kept for transparency: explanations, warnings, cost lines and totals (all estimates).
    generation_report: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    itinerary: Mapped[Itinerary] = relationship(back_populates="versions")
    days: Mapped[list["ItineraryDay"]] = relationship(back_populates="version", cascade="all, delete-orphan", order_by="ItineraryDay.day_number")
    stays: Mapped[list["ItineraryStay"]] = relationship(back_populates="version", cascade="all, delete-orphan", order_by="ItineraryStay.check_in_day")
    transports: Mapped[list["ItineraryTransport"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", order_by="[ItineraryTransport.day_number, ItineraryTransport.sort_order]"
    )


class ItineraryDay(IdMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_days"
    __table_args__ = (UniqueConstraint("version_id", "day_number", name="uq_itinerary_days_number"),)

    version_id: Mapped[int] = mapped_column(ForeignKey("itinerary_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False)
    overnight_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    version: Mapped[ItineraryVersion] = relationship(back_populates="days")
    activities: Mapped[list["ItineraryActivity"]] = relationship(back_populates="day", cascade="all, delete-orphan", order_by="ItineraryActivity.sort_order")
    meals: Mapped[list["ItineraryMeal"]] = relationship(back_populates="day", cascade="all, delete-orphan", order_by="ItineraryMeal.sort_order")


class ItineraryActivity(IdMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_activities"

    day_id: Mapped[int] = mapped_column(ForeignKey("itinerary_days.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_slot: Mapped[str] = mapped_column(String(20), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    attraction_id: Mapped[int | None] = mapped_column(ForeignKey("attractions.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_min: Mapped[int | None] = mapped_column(Integer)

    day: Mapped[ItineraryDay] = relationship(back_populates="activities")


class ItineraryMeal(IdMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_meals"

    day_id: Mapped[int] = mapped_column(ForeignKey("itinerary_days.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meal: Mapped[str] = mapped_column(String(20), nullable=False)
    arrangement: Mapped[str] = mapped_column(String(20), nullable=False)  # hotel / restaurant / own
    restaurant_id: Mapped[int | None] = mapped_column(ForeignKey("restaurants.id", ondelete="RESTRICT"))
    note: Mapped[str | None] = mapped_column(String(500))

    day: Mapped[ItineraryDay] = relationship(back_populates="meals")


class ItineraryStay(IdMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_stays"

    version_id: Mapped[int] = mapped_column(ForeignKey("itinerary_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False)
    hotel_id: Mapped[int | None] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"))
    check_in_day: Mapped[int] = mapped_column(Integer, nullable=False)
    nights: Mapped[int] = mapped_column(Integer, nullable=False)
    rooms: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)  # [{room_type_id, label, count, price}]
    alternative_hotel_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    note: Mapped[str | None] = mapped_column(String(500))

    version: Mapped[ItineraryVersion] = relationship(back_populates="stays")


class ItineraryTransport(IdMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_transports"

    version_id: Mapped[int] = mapped_column(ForeignKey("itinerary_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # airport_transfer / intercity
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # coach / minibus / car / train
    from_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    to_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    distance_km: Mapped[int | None] = mapped_column(Integer)
    duration_min: Mapped[int | None] = mapped_column(Integer)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))

    version: Mapped[ItineraryVersion] = relationship(back_populates="transports")
