"""CRM use cases: travel agents, customers, enquiries and the enquiry status workflow."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Customer, Enquiry, EnquiryStatusHistory, TravelAgent, User
from app.models.enums import AgentStatus, EnquiryStatus
from app.repositories.crm import CustomerRepository, EnquiryRepository, TravelAgentRepository
from app.repositories.users import UserRepository
from app.schemas.common import Page, PageParams
from app.schemas.crm import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    DashboardSummary,
    EnquiryCreate,
    EnquiryOut,
    EnquiryStatusChange,
    EnquiryUpdate,
    TravelAgentCreate,
    TravelAgentOut,
    TravelAgentUpdate,
)

ENQUIRY_PREFIX = "ENQ"


def _not_found(what: str) -> DomainError:
    return DomainError(f"{what} not found.", status.HTTP_404_NOT_FOUND, "not_found")


class TravelAgentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TravelAgentRepository(db)

    def list(self, q, status_, country, page: PageParams) -> Page[TravelAgentOut]:
        items, total = self.repo.list(q, status_, country, page.offset, page.page_size)
        counts = self.repo.counts([a.id for a in items])
        return Page(
            items=[self._out(a, counts.get(a.id, (0, 0))) for a in items],
            total=total, page=page.page, page_size=page.page_size,
        )

    def get(self, agent_id: int) -> TravelAgentOut:
        agent = self._get(agent_id)
        return self._out(agent, self.repo.counts([agent.id])[agent.id])

    def create(self, data: TravelAgentCreate) -> TravelAgentOut:
        agent = self.repo.add(TravelAgent(**data.model_dump()))
        self.db.commit()
        return self._out(agent, (0, 0))

    def update(self, agent_id: int, data: TravelAgentUpdate) -> TravelAgentOut:
        agent = self._get(agent_id)
        for key, value in data.model_dump().items():
            setattr(agent, key, value)
        self.db.commit()
        return self.get(agent_id)

    def set_status(self, agent_id: int, new_status: AgentStatus) -> TravelAgentOut:
        agent = self._get(agent_id)
        agent.status = new_status
        self.db.commit()
        return self.get(agent_id)

    def countries(self) -> list[str]:
        return self.repo.countries()

    def _get(self, agent_id: int) -> TravelAgent:
        agent = self.repo.get(agent_id)
        if not agent:
            raise _not_found("Travel agent")
        return agent

    @staticmethod
    def _out(agent: TravelAgent, counts: tuple[int, int]) -> TravelAgentOut:
        return TravelAgentOut.model_validate(agent).model_copy(
            update={"customer_count": counts[0], "enquiry_count": counts[1]}
        )


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CustomerRepository(db)
        self.agents = TravelAgentRepository(db)

    def list(self, q, travel_agent_id, active, page: PageParams) -> Page[CustomerOut]:
        items, total = self.repo.list(q, travel_agent_id, active, page.offset, page.page_size)
        counts = self.repo.enquiry_counts([c.id for c in items])
        return Page(
            items=[self._out(c, counts.get(c.id, 0)) for c in items],
            total=total, page=page.page, page_size=page.page_size,
        )

    def get(self, customer_id: int) -> CustomerOut:
        customer = self._get(customer_id)
        return self._out(customer, self.repo.enquiry_counts([customer.id]).get(customer.id, 0))

    def create(self, data: CustomerCreate) -> CustomerOut:
        self._check_agent(data.travel_agent_id)
        customer = self.repo.add(Customer(**data.model_dump()))
        self.db.commit()
        return self.get(customer.id)

    def update(self, customer_id: int, data: CustomerUpdate) -> CustomerOut:
        customer = self._get(customer_id)
        if data.travel_agent_id != customer.travel_agent_id:
            self._check_agent(data.travel_agent_id)
        for key, value in data.model_dump().items():
            setattr(customer, key, value)
        self.db.commit()
        self.db.refresh(customer)
        return self.get(customer_id)

    def _check_agent(self, agent_id: int | None) -> None:
        if agent_id is None:
            return
        agent = self.agents.get(agent_id)
        if not agent:
            raise DomainError("Selected travel agent does not exist.", status.HTTP_400_BAD_REQUEST, "invalid_agent")
        if agent.status != AgentStatus.ACTIVE:
            raise DomainError("Selected travel agent is inactive.", status.HTTP_400_BAD_REQUEST, "inactive_agent")

    def _get(self, customer_id: int) -> Customer:
        customer = self.repo.get(customer_id)
        if not customer:
            raise _not_found("Customer")
        return customer

    @staticmethod
    def _out(customer: Customer, enquiry_count: int) -> CustomerOut:
        return CustomerOut.model_validate(customer).model_copy(update={"enquiry_count": enquiry_count})


class EnquiryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnquiryRepository(db)
        self.agents = TravelAgentRepository(db)
        self.customers = CustomerRepository(db)
        self.users = UserRepository(db)

    def list(self, filters: dict, page: PageParams) -> Page[EnquiryOut]:
        items, total = self.repo.list(**filters, offset=page.offset, limit=page.page_size)
        return Page(
            items=[EnquiryOut.model_validate(e) for e in items], total=total, page=page.page, page_size=page.page_size
        )

    def get(self, enquiry_id: int) -> Enquiry:
        enquiry = self.repo.get(enquiry_id)
        if not enquiry:
            raise _not_found("Enquiry")
        return enquiry

    def create(self, data: EnquiryCreate, acting_user: User) -> Enquiry:
        self._validate_refs(data, is_new=True)
        enquiry = Enquiry(
            **data.model_dump(),
            reference=self.repo.next_reference(ENQUIRY_PREFIX, data.enquiry_date.year),
            status=EnquiryStatus.NEW,
        )
        enquiry.status_history.append(
            EnquiryStatusHistory(from_status=None, to_status=EnquiryStatus.NEW, changed_by_id=acting_user.id, note="Enquiry created")
        )
        self.repo.add(enquiry)
        self.db.commit()
        return self.get(enquiry.id)

    def update(self, enquiry_id: int, data: EnquiryUpdate) -> Enquiry:
        enquiry = self.get(enquiry_id)
        self._validate_refs(data, is_new=False, current=enquiry)
        for key, value in data.model_dump().items():
            setattr(enquiry, key, value)
        self.db.commit()
        self.db.expire_all()
        return self.get(enquiry_id)

    def change_status(self, enquiry_id: int, change: EnquiryStatusChange, acting_user: User) -> Enquiry:
        enquiry = self.get(enquiry_id)
        if enquiry.status == change.status:
            raise DomainError("The enquiry already has this status.", status.HTTP_409_CONFLICT, "status_unchanged")
        enquiry.status_history.append(
            EnquiryStatusHistory(
                from_status=enquiry.status, to_status=change.status, changed_by_id=acting_user.id, note=change.note
            )
        )
        enquiry.status = change.status
        self.db.commit()
        self.db.expire_all()
        return self.get(enquiry_id)

    def dashboard(self) -> DashboardSummary:
        counts = self.repo.status_counts()
        return DashboardSummary(
            total_enquiries=sum(counts.values()),
            by_status={s: counts.get(s.value, 0) for s in EnquiryStatus},
            active_agents=self.agents.count_active(),
            customers=self.customers.count_active(),
            recent_enquiries=[EnquiryOut.model_validate(e) for e in self.repo.recent(6)],
        )

    def _validate_refs(self, data: EnquiryCreate, is_new: bool, current: Enquiry | None = None) -> None:
        agent = self.agents.get(data.travel_agent_id)
        if not agent:
            raise DomainError("Selected travel agent does not exist.", status.HTTP_400_BAD_REQUEST, "invalid_agent")
        agent_changed = is_new or (current and current.travel_agent_id != data.travel_agent_id)
        if agent_changed and agent.status != AgentStatus.ACTIVE:
            raise DomainError("Selected travel agent is inactive.", status.HTTP_400_BAD_REQUEST, "inactive_agent")

        customer = self.customers.get(data.customer_id)
        if not customer:
            raise DomainError("Selected customer does not exist.", status.HTTP_400_BAD_REQUEST, "invalid_customer")
        if customer.travel_agent_id not in (None, data.travel_agent_id):
            raise DomainError(
                "This customer belongs to a different travel agent.", status.HTTP_400_BAD_REQUEST, "customer_agent_mismatch"
            )

        if data.assigned_planner_id is not None:
            planner = self.users.get(data.assigned_planner_id)
            if not planner or not planner.is_active:
                raise DomainError("Assigned planner is not an active user.", status.HTTP_400_BAD_REQUEST, "invalid_planner")
