"""CRM endpoints. Available to all signed-in roles (admin and planner)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.api.deps import DB, CurrentUser, Pagination
from app.models.enums import AgentStatus, EnquiryStatus
from app.schemas.common import Page
from app.schemas.crm import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    DashboardSummary,
    EnquiryCreate,
    EnquiryDetail,
    EnquiryOut,
    EnquiryStatusChange,
    EnquiryUpdate,
    TravelAgentCreate,
    TravelAgentOut,
    TravelAgentUpdate,
)
from app.schemas.requirements import RequirementIn, RequirementOptions, RequirementOut
from app.services.crm_service import CustomerService, EnquiryService, TravelAgentService
from app.services.requirement_service import RequirementService

agents = APIRouter(prefix="/travel-agents", tags=["CRM: Travel agents"])
customers = APIRouter(prefix="/customers", tags=["CRM: Customers"])
enquiries = APIRouter(prefix="/enquiries", tags=["CRM: Enquiries"])
dashboard = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class AgentStatusBody(BaseModel):
    status: AgentStatus


# ------------------------------------------------------------------ travel agents
@agents.get("", response_model=Page[TravelAgentOut])
def list_agents(db: DB, _: CurrentUser, page: Pagination, q: str | None = None,
                status_: Annotated[AgentStatus | None, Query(alias="status")] = None, country: str | None = None):
    return TravelAgentService(db).list(q, status_, country, page)


@agents.get("/countries", response_model=list[str], summary="Distinct agent countries (for filters)")
def agent_countries(db: DB, _: CurrentUser):
    return TravelAgentService(db).countries()


@agents.get("/{agent_id}", response_model=TravelAgentOut)
def get_agent(agent_id: int, db: DB, _: CurrentUser):
    return TravelAgentService(db).get(agent_id)


@agents.post("", response_model=TravelAgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(body: TravelAgentCreate, db: DB, _: CurrentUser):
    return TravelAgentService(db).create(body)


@agents.put("/{agent_id}", response_model=TravelAgentOut)
def update_agent(agent_id: int, body: TravelAgentUpdate, db: DB, _: CurrentUser):
    return TravelAgentService(db).update(agent_id, body)


@agents.patch("/{agent_id}/status", response_model=TravelAgentOut, summary="Activate or deactivate an agent")
def set_agent_status(agent_id: int, body: AgentStatusBody, db: DB, _: CurrentUser):
    return TravelAgentService(db).set_status(agent_id, body.status)


# ------------------------------------------------------------------ customers
@customers.get("", response_model=Page[CustomerOut])
def list_customers(db: DB, _: CurrentUser, page: Pagination, q: str | None = None,
                   travel_agent_id: int | None = None, active: bool | None = None):
    return CustomerService(db).list(q, travel_agent_id, active, page)


@customers.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: DB, _: CurrentUser):
    return CustomerService(db).get(customer_id)


@customers.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, db: DB, _: CurrentUser):
    return CustomerService(db).create(body)


@customers.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, body: CustomerUpdate, db: DB, _: CurrentUser):
    return CustomerService(db).update(customer_id, body)


# ------------------------------------------------------------------ enquiries
@enquiries.get("", response_model=Page[EnquiryOut])
def list_enquiries(
    db: DB, _: CurrentUser, page: Pagination, q: str | None = None, status_: Annotated[EnquiryStatus | None, Query(alias="status")] = None,
    travel_agent_id: int | None = None, customer_id: int | None = None, assigned_planner_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None,
):
    filters = dict(q=q, status=status_, travel_agent_id=travel_agent_id, customer_id=customer_id,
                   assigned_planner_id=assigned_planner_id, date_from=date_from, date_to=date_to)
    return EnquiryService(db).list(filters, page)


@enquiries.get("/{enquiry_id}", response_model=EnquiryDetail)
def get_enquiry(enquiry_id: int, db: DB, _: CurrentUser):
    return EnquiryService(db).get(enquiry_id)


@enquiries.post("", response_model=EnquiryDetail, status_code=status.HTTP_201_CREATED)
def create_enquiry(body: EnquiryCreate, db: DB, user: CurrentUser):
    return EnquiryService(db).create(body, user)


@enquiries.put("/{enquiry_id}", response_model=EnquiryDetail)
def update_enquiry(enquiry_id: int, body: EnquiryUpdate, db: DB, _: CurrentUser):
    return EnquiryService(db).update(enquiry_id, body)


@enquiries.post("/{enquiry_id}/status", response_model=EnquiryDetail, summary="Change status (recorded in history)")
def change_enquiry_status(enquiry_id: int, body: EnquiryStatusChange, db: DB, user: CurrentUser):
    return EnquiryService(db).change_status(enquiry_id, body, user)


@enquiries.get("/requirements/options", response_model=RequirementOptions, summary="Vocabularies for the requirement form")
def requirement_options(_: CurrentUser):
    return RequirementOptions()


@enquiries.get("/{enquiry_id}/requirements", response_model=RequirementOut,
               summary="Customer requirements (pre-filled defaults if not captured yet; `exists=false`)")
def get_requirements(enquiry_id: int, db: DB, _: CurrentUser):
    return RequirementService(db).get(enquiry_id)


@enquiries.put("/{enquiry_id}/requirements", response_model=RequirementOut,
               summary="Save requirements (draft-friendly; returns `missing` and `warnings`)")
def save_requirements(enquiry_id: int, body: RequirementIn, db: DB, user: CurrentUser):
    return RequirementService(db).save(enquiry_id, body, user)


# ------------------------------------------------------------------ dashboard
@dashboard.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: DB, _: CurrentUser):
    return EnquiryService(db).dashboard()
