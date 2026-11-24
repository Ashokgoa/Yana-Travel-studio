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
from app.models.itinerary import (
    Itinerary,
    ItineraryActivity,
    ItineraryDay,
    ItineraryMeal,
    ItineraryStay,
    ItineraryTransport,
    ItineraryVersion,
)
from app.models.media import Media, MediaLink
from app.models.pricing import PricingLine, PricingSheet, SupplierRate
from app.models.proposal import ProposalExport
from app.models.requirements import EnquiryDestination, EnquiryRequirement
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
    "EnquiryDestination",
    "EnquiryRequirement",
    "EnquiryStatusHistory",
    "Hotel",
    "HotelRate",
    "HotelRoomType",
    "Itinerary",
    "ItineraryActivity",
    "ItineraryDay",
    "ItineraryMeal",
    "ItineraryStay",
    "ItineraryTransport",
    "ItineraryVersion",
    "Media",
    "MediaLink",
    "PricingLine",
    "PricingSheet",
    "ProposalExport",
    "ReferenceCounter",
    "Restaurant",
    "Role",
    "Supplier",
    "SupplierRate",
    "TravelAgent",
    "User",
    "Vehicle",
    "VehicleCategory",
    "vehicle_countries",
]
