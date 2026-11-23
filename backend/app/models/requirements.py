"""Structured customer requirements for an enquiry (PRD Part 7).

One `EnquiryRequirement` per enquiry holds the 9-step capture form. Multi-select
choices are stored as JSON lists of validated vocabulary codes; destinations
(which need foreign keys) live in `EnquiryDestination`.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin
from app.models.inventory import City, Country


class EnquiryRequirement(IdMixin, TimestampMixin, Base):
    __tablename__ = "enquiry_requirements"

    enquiry_id: Mapped[int] = mapped_column(ForeignKey("enquiries.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Step 1 – travellers (agent/customer live on the enquiry)
    adults: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    children_ages: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)

    # Step 2 – travel
    arrival_date: Mapped[date | None] = mapped_column(Date)
    departure_date: Mapped[date | None] = mapped_column(Date)
    arrival_airport: Mapped[str | None] = mapped_column(String(100))
    departure_airport: Mapped[str | None] = mapped_column(String(100))
    start_country_id: Mapped[int | None] = mapped_column(ForeignKey("countries.id", ondelete="SET NULL"))
    end_country_id: Mapped[int | None] = mapped_column(ForeignKey("countries.id", ondelete="SET NULL"))
    travel_type: Mapped[str | None] = mapped_column(String(3))  # FIT / GIT
    group_size: Mapped[int | None] = mapped_column(Integer)

    # Step 4 – interests
    interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    travel_pace: Mapped[str | None] = mapped_column(String(20))  # relaxed / balanced / fast

    # Step 5 – hotels
    hotel_categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hotel_locations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    breakfast_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rooms: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)  # [{"type": "double", "count": 2}]

    # Step 6 – food
    food_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    meals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)  # breakfast / lunch / dinner

    # Step 7 – transport
    transport_modes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    passenger_capacity: Mapped[int | None] = mapped_column(Integer)
    luggage_notes: Mapped[str | None] = mapped_column(String(500))
    airport_transfers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    local_sightseeing_transport: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Step 8 – budget
    budget_per_person: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    budget_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    budget_flexibility: Mapped[str | None] = mapped_column(String(20))  # strict / some / flexible
    travel_class: Mapped[str | None] = mapped_column(String(20))  # budget / standard / premium / luxury

    # Step 9 – additional
    additional_requirements: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)

    completed_steps: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    destinations: Mapped[list["EnquiryDestination"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan", order_by="EnquiryDestination.sort_order"
    )
    start_country: Mapped[Country | None] = relationship(foreign_keys=[start_country_id])
    end_country: Mapped[Country | None] = relationship(foreign_keys=[end_country_id])


class EnquiryDestination(IdMixin, TimestampMixin, Base):
    """A country (optionally a specific city) with the customer's preference for it."""

    __tablename__ = "enquiry_destinations"

    requirement_id: Mapped[int] = mapped_column(ForeignKey("enquiry_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    preference: Mapped[str] = mapped_column(String(20), nullable=False)  # mandatory / preferred / optional / avoid
    min_nights: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    requirement: Mapped[EnquiryRequirement] = relationship(back_populates="destinations")
    country: Mapped[Country] = relationship()
    city: Mapped[City | None] = relationship()
