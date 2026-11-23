from __future__ import annotations

from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import joinedload, selectinload

from app.models import Customer, Enquiry, EnquiryStatusHistory, ReferenceCounter, TravelAgent
from app.repositories.base import Repository, search_filter


class TravelAgentRepository(Repository[TravelAgent]):
    model = TravelAgent

    def list(self, q: str | None, status: str | None, country: str | None, offset: int, limit: int):
        stmt = select(TravelAgent).order_by(TravelAgent.company_name)
        if q:
            stmt = stmt.where(
                search_filter(q, TravelAgent.company_name, TravelAgent.contact_person, TravelAgent.email, TravelAgent.phone)
            )
        if status:
            stmt = stmt.where(TravelAgent.status == status)
        if country:
            stmt = stmt.where(func.lower(TravelAgent.country) == country.lower())
        return self.paginate(stmt, offset, limit)

    def counts(self, agent_ids: list[int]) -> dict[int, tuple[int, int]]:
        """(customer_count, enquiry_count) per agent id."""
        if not agent_ids:
            return {}
        customers = dict(
            self.db.execute(
                select(Customer.travel_agent_id, func.count()).where(Customer.travel_agent_id.in_(agent_ids))
                .group_by(Customer.travel_agent_id)
            ).all()
        )
        enquiries = dict(
            self.db.execute(
                select(Enquiry.travel_agent_id, func.count()).where(Enquiry.travel_agent_id.in_(agent_ids))
                .group_by(Enquiry.travel_agent_id)
            ).all()
        )
        return {i: (customers.get(i, 0), enquiries.get(i, 0)) for i in agent_ids}

    def countries(self) -> list[str]:
        rows = self.db.scalars(
            select(TravelAgent.country).where(TravelAgent.country.is_not(None)).distinct().order_by(TravelAgent.country)
        )
        return list(rows)

    def count_active(self) -> int:
        return self.db.scalar(select(func.count()).where(TravelAgent.status == "active")) or 0


class CustomerRepository(Repository[Customer]):
    model = Customer

    def get(self, entity_id: int) -> Customer | None:
        return self.db.scalar(
            select(Customer).options(joinedload(Customer.travel_agent)).where(Customer.id == entity_id)
        )

    def list(self, q: str | None, travel_agent_id: int | None, active: bool | None, offset: int, limit: int):
        stmt = select(Customer).options(joinedload(Customer.travel_agent)).order_by(Customer.name)
        if q:
            stmt = stmt.where(search_filter(q, Customer.name, Customer.email, Customer.phone))
        if travel_agent_id:
            stmt = stmt.where(Customer.travel_agent_id == travel_agent_id)
        if active is not None:
            stmt = stmt.where(Customer.is_active == active)
        return self.paginate(stmt, offset, limit)

    def enquiry_counts(self, customer_ids: list[int]) -> dict[int, int]:
        if not customer_ids:
            return {}
        return dict(
            self.db.execute(
                select(Enquiry.customer_id, func.count()).where(Enquiry.customer_id.in_(customer_ids))
                .group_by(Enquiry.customer_id)
            ).all()
        )

    def count_active(self) -> int:
        return self.db.scalar(select(func.count()).where(Customer.is_active.is_(True))) or 0


_ENQUIRY_LOAD = (
    joinedload(Enquiry.travel_agent),
    joinedload(Enquiry.customer),
    joinedload(Enquiry.assigned_planner),
)


class EnquiryRepository(Repository[Enquiry]):
    model = Enquiry

    def get(self, entity_id: int) -> Enquiry | None:
        return self.db.scalar(
            select(Enquiry)
            .options(*_ENQUIRY_LOAD, selectinload(Enquiry.status_history).joinedload(EnquiryStatusHistory.changed_by))
            .where(Enquiry.id == entity_id)
        )

    def list(
        self,
        q: str | None,
        status: str | None,
        travel_agent_id: int | None,
        customer_id: int | None,
        assigned_planner_id: int | None,
        date_from: date | None,
        date_to: date | None,
        offset: int,
        limit: int,
    ):
        stmt = (
            select(Enquiry)
            .join(Enquiry.travel_agent)
            .join(Enquiry.customer)
            .options(*_ENQUIRY_LOAD)
            .order_by(Enquiry.enquiry_date.desc(), Enquiry.id.desc())
        )
        if q:
            stmt = stmt.where(
                search_filter(q, Enquiry.reference, Customer.name, TravelAgent.company_name, Enquiry.destination_preferences)
            )
        if status:
            stmt = stmt.where(Enquiry.status == status)
        if travel_agent_id:
            stmt = stmt.where(Enquiry.travel_agent_id == travel_agent_id)
        if customer_id:
            stmt = stmt.where(Enquiry.customer_id == customer_id)
        if assigned_planner_id:
            stmt = stmt.where(Enquiry.assigned_planner_id == assigned_planner_id)
        if date_from:
            stmt = stmt.where(Enquiry.enquiry_date >= date_from)
        if date_to:
            stmt = stmt.where(Enquiry.enquiry_date <= date_to)
        return self.paginate(stmt, offset, limit)

    def status_counts(self) -> dict[str, int]:
        return dict(self.db.execute(select(Enquiry.status, func.count()).group_by(Enquiry.status)).all())

    def recent(self, limit: int = 5) -> list[Enquiry]:
        return list(
            self.db.scalars(select(Enquiry).options(*_ENQUIRY_LOAD).order_by(Enquiry.created_at.desc(), Enquiry.id.desc()).limit(limit))
        )

    def next_reference(self, prefix: str, year: int) -> str:
        """Atomically increment the per-year counter and return e.g. ENQ-2026-0001."""
        result = self.db.execute(
            update(ReferenceCounter)
            .where(ReferenceCounter.prefix == prefix, ReferenceCounter.year == year)
            .values(last_value=ReferenceCounter.last_value + 1)
            .returning(ReferenceCounter.last_value)
        ).scalar()
        if result is None:
            self.db.add(ReferenceCounter(prefix=prefix, year=year, last_value=1))
            self.db.flush()
            result = 1
        return f"{prefix}-{year}-{result:04d}"
