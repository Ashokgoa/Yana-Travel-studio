"""Domain enumerations. Stored as plain strings in the DB (portable, migration-friendly)
and validated by Pydantic at the API boundary."""

from enum import StrEnum


class RoleCode(StrEnum):
    ADMIN = "admin"
    PLANNER = "planner"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class EnquiryStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    PROPOSAL_GENERATED = "proposal_generated"
    SENT_TO_AGENT = "sent_to_agent"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    BOOKING_CONFIRMED = "booking_confirmed"
    CANCELLED = "cancelled"


class BudgetBasis(StrEnum):
    PER_PERSON = "per_person"
    TOTAL = "total"
