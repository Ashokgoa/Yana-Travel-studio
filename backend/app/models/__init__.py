"""Import every model here so Alembic autogenerate sees the full metadata."""

from app.database.base import Base
from app.models.crm import Customer, Enquiry, EnquiryStatusHistory, ReferenceCounter, TravelAgent
from app.models.inventory import (
    Attraction,
    City,
    Country,
    Hotel,
    HotelRate,
    HotelRoomType,
    Restaurant,
    Supplier,
    Vehicle,
    VehicleCategory,
    vehicle_countries,
)
from app.models.media import Media, MediaLink
from app.models.setting import AppSetting
from app.models.user import Role, User

__all__ = [
    "Base",
    "AppSetting",
    "Attraction",
    "City",
    "Country",
    "Customer",
    "Enquiry",
    "EnquiryStatusHistory",
    "Hotel",
    "HotelRate",
    "HotelRoomType",
    "Media",
    "MediaLink",
    "ReferenceCounter",
    "Restaurant",
    "Role",
    "Supplier",
    "TravelAgent",
    "User",
    "Vehicle",
    "VehicleCategory",
    "vehicle_countries",
]
