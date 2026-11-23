"""CRM request/response schemas (travel agents, customers, enquiries)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AgentStatus, BudgetBasis, EnquiryStatus
from app.schemas.common import CurrencyCode, OptEmail, OptStr, ORMModel, RequiredStr

# ---------------------------------------------------------------- Travel agents


class TravelAgentBase(BaseModel):
    company_name: RequiredStr = Field(max_length=200)
    contact_person: OptStr = Field(default=None, max_length=200)
    email: OptEmail = None
    phone: OptStr = Field(default=None, max_length=50)
    country: OptStr = Field(default=None, max_length=100)
    address: OptStr = Field(default=None, max_length=500)
    company_details: OptStr = None
    internal_notes: OptStr = None


class TravelAgentCreate(TravelAgentBase):
    status: AgentStatus = AgentStatus.ACTIVE


class TravelAgentUpdate(TravelAgentCreate):
    """Full replacement update (PUT)."""


class TravelAgentOut(TravelAgentBase, ORMModel):
    id: int
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
    customer_count: int = 0
    enquiry_count: int = 0


class TravelAgentRef(ORMModel):
    id: int
    company_name: str
    status: AgentStatus


# ---------------------------------------------------------------- Customers


class CustomerBase(BaseModel):
    travel_agent_id: int | None = None
    name: RequiredStr = Field(max_length=200)
    phone: OptStr = Field(default=None, max_length=50)
    email: OptEmail = None
    nationality: OptStr = Field(default=None, max_length=100)
    country_of_residence: OptStr = Field(default=None, max_length=100)
    adults: int = Field(default=1, ge=0, le=500)
    children: int = Field(default=0, ge=0, le=500)
    children_ages: list[int] = Field(default_factory=list)
    special_requirements: OptStr = None

    @model_validator(mode="after")
    def _check_travellers(self):
        if self.adults + self.children < 1:
            raise ValueError("At least one traveller is required.")
        if len(self.children_ages) != self.children:
            raise ValueError(f"Provide an age for each child ({self.children} expected, {len(self.children_ages)} given).")
        if any(age < 0 or age > 17 for age in self.children_ages):
            raise ValueError("Children's ages must be between 0 and 17.")
        return self


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    is_active: bool = True


class CustomerOut(CustomerBase, ORMModel):
    id: int
    is_active: bool
    travel_agent: TravelAgentRef | None = None
    created_at: datetime
    updated_at: datetime
    enquiry_count: int = 0


class CustomerRef(ORMModel):
    id: int
    name: str


# ---------------------------------------------------------------- Enquiries


class PlannerRef(ORMModel):
    id: int
    full_name: str


class EnquiryBase(BaseModel):
    travel_agent_id: int
    customer_id: int
    enquiry_date: date = Field(default_factory=date.today)
    travel_start_date: date | None = None
    travel_end_date: date | None = None
    adults: int = Field(default=1, ge=0, le=500)
    children: int = Field(default=0, ge=0, le=500)
    destination_preferences: OptStr = None
    budget_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    budget_currency: CurrencyCode = "EUR"
    budget_basis: BudgetBasis | None = None
    assigned_planner_id: int | None = None
    internal_comments: OptStr = None

    @model_validator(mode="after")
    def _check(self):
        if self.adults + self.children < 1:
            raise ValueError("At least one traveller is required.")
        if self.travel_start_date and self.travel_end_date and self.travel_end_date < self.travel_start_date:
            raise ValueError("Travel end date cannot be before the start date.")
        if self.budget_amount is not None and self.budget_basis is None:
            raise ValueError("Specify whether the budget is per person or for the whole group.")
        return self


class EnquiryCreate(EnquiryBase):
    pass


class EnquiryUpdate(EnquiryBase):
    pass


class EnquiryStatusChange(BaseModel):
    status: EnquiryStatus
    note: OptStr = Field(default=None, max_length=1000)


class StatusHistoryOut(ORMModel):
    id: int
    from_status: EnquiryStatus | None
    to_status: EnquiryStatus
    note: str | None
    changed_by: PlannerRef | None
    created_at: datetime


class EnquiryOut(EnquiryBase, ORMModel):
    id: int
    reference: str
    status: EnquiryStatus
    travel_agent: TravelAgentRef
    customer: CustomerRef
    assigned_planner: PlannerRef | None
    total_travellers: int
    created_at: datetime
    updated_at: datetime


class EnquiryDetail(EnquiryOut):
    status_history: list[StatusHistoryOut]


# ---------------------------------------------------------------- Dashboard


class DashboardSummary(BaseModel):
    total_enquiries: int
    by_status: dict[EnquiryStatus, int]
    active_agents: int
    customers: int
    recent_enquiries: list[EnquiryOut]
