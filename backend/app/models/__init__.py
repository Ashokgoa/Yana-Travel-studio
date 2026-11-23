"""Import every model here so Alembic autogenerate sees the full metadata."""

from app.database.base import Base
from app.models.crm import Customer, Enquiry, EnquiryStatusHistory, ReferenceCounter, TravelAgent
from app.models.setting import AppSetting
from app.models.user import Role, User

__all__ = [
    "Base",
    "AppSetting",
    "Customer",
    "Enquiry",
    "EnquiryStatusHistory",
    "ReferenceCounter",
    "Role",
    "TravelAgent",
    "User",
]
