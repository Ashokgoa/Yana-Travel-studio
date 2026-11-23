"""CRM: travel agents, customers, enquiries (PRD Part 6)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin
from app.models.enums import AgentStatus, EnquiryStatus
from app.models.user import User


class TravelAgent(IdMixin, TimestampMixin, Base):
    __tablename__ = "travel_agents"

    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    # Free text: agents are often outside the European destination inventory (e.g. India).
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    company_details: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=AgentStatus.ACTIVE, nullable=False, index=True)

    customers: Mapped[list["Customer"]] = relationship(back_populates="travel_agent")
    enquiries: Mapped[list["Enquiry"]] = relationship(back_populates="travel_agent")


class Customer(IdMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    travel_agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("travel_agents.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    nationality: Mapped[str | None] = mapped_column(String(100))
    country_of_residence: Mapped[str | None] = mapped_column(String(100))
    adults: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    children_ages: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    special_requirements: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    travel_agent: Mapped[TravelAgent | None] = relationship(back_populates="customers")
    enquiries: Mapped[list["Enquiry"]] = relationship(back_populates="customer")


class Enquiry(IdMixin, TimestampMixin, Base):
    __tablename__ = "enquiries"

    reference: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    travel_agent_id: Mapped[int] = mapped_column(
        ForeignKey("travel_agents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    enquiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    travel_start_date: Mapped[date | None] = mapped_column(Date)
    travel_end_date: Mapped[date | None] = mapped_column(Date)
    adults: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Free-text summary for now; structured destinations arrive with Phase 3 requirements.
    destination_preferences: Mapped[str | None] = mapped_column(Text)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    budget_currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    budget_basis: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default=EnquiryStatus.NEW, nullable=False, index=True)
    assigned_planner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    internal_comments: Mapped[str | None] = mapped_column(Text)

    travel_agent: Mapped[TravelAgent] = relationship(back_populates="enquiries")
    customer: Mapped[Customer] = relationship(back_populates="enquiries")
    assigned_planner: Mapped[User | None] = relationship()
    status_history: Mapped[list["EnquiryStatusHistory"]] = relationship(
        back_populates="enquiry", cascade="all, delete-orphan", order_by="EnquiryStatusHistory.id"
    )

    @property
    def total_travellers(self) -> int:
        return self.adults + self.children


class EnquiryStatusHistory(IdMixin, TimestampMixin, Base):
    __tablename__ = "enquiry_status_history"

    enquiry_id: Mapped[int] = mapped_column(ForeignKey("enquiries.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(1000))

    enquiry: Mapped[Enquiry] = relationship(back_populates="status_history")
    changed_by: Mapped[User | None] = relationship()


class ReferenceCounter(IdMixin, TimestampMixin, Base):
    """Per-prefix, per-year counters for human-readable references (ENQ-2026-0001)."""

    __tablename__ = "reference_counters"
    __table_args__ = (UniqueConstraint("prefix", "year", name="uq_reference_counters_prefix_year"),)

    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
