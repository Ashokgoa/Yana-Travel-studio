"""Inventory endpoints. Read: any signed-in user. Write: administrators only (PRD Part 2).

No `from __future__ import annotations` here: FastAPI must see the real body
types of the routes generated inside `_register`.
"""

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select

from app.api.deps import DB, AdminUser, CurrentUser, Pagination
from app.core.errors import DomainError
from app.models import Hotel, HotelRate, HotelRoomType, VehicleCategory
from app.schemas.common import Page
from app.schemas.inventory import (
    HotelOut,
    InventoryOptions,
    RateIn,
    RoomTypeIn,
    StatusBody,
    VehicleCategoryOut,
)
from app.services.inventory_resources import RESOURCES
from app.services.inventory_service import InventoryService, Resource

RESERVED_QUERY = {"q", "active", "page", "page_size"}

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/options", response_model=InventoryOptions, summary="Vocabularies for inventory forms and filters")
def options(_: CurrentUser):
    return InventoryOptions()


@router.get("/vehicle-categories", response_model=list[VehicleCategoryOut])
def vehicle_categories(db: DB, _: CurrentUser):
    return list(db.scalars(select(VehicleCategory).order_by(VehicleCategory.sort_order)))


def _register(resource: Resource) -> None:
    """Adds list / get / create / update / status endpoints for one resource."""
    base = f"/{resource.name}"
    In, Out = resource.schema_in, resource.schema_out
    tag = [f"Inventory: {resource.label}s"]

    def list_items(request: Request, db: DB, _: CurrentUser, page: Pagination,
                   q: str | None = None, active: bool | None = Query(default=None)):
        raw = {k: v for k, v in request.query_params.items() if k not in RESERVED_QUERY}
        return InventoryService(db, resource).list(q, active, raw, page)

    def get_item(item_id: int, db: DB, _: CurrentUser):
        return InventoryService(db, resource).get(item_id)

    def create_item(body: In, db: DB, _: AdminUser):  # type: ignore[valid-type]
        return InventoryService(db, resource).create(body)

    def update_item(item_id: int, body: In, db: DB, _: AdminUser):  # type: ignore[valid-type]
        return InventoryService(db, resource).update(item_id, body)

    def set_status(item_id: int, body: StatusBody, db: DB, _: AdminUser):
        return InventoryService(db, resource).set_active(item_id, body.is_active)

    filters = ", ".join(resource.filters) or "none"
    router.add_api_route(base, list_items, methods=["GET"], response_model=Page[Out], tags=tag,
                         summary=f"List {resource.name}", description=f"Search with `q`. Filters: {filters}. `active=true|false`.")
    router.add_api_route(f"{base}/{{item_id}}", get_item, methods=["GET"], response_model=Out, tags=tag,
                         summary=f"Get {resource.label.lower()}")
    router.add_api_route(base, create_item, methods=["POST"], response_model=Out, status_code=status.HTTP_201_CREATED,
                         tags=tag, summary=f"Create {resource.label.lower()} (admin)")
    router.add_api_route(f"{base}/{{item_id}}", update_item, methods=["PUT"], response_model=Out, tags=tag,
                         summary=f"Update {resource.label.lower()} (admin)")
    router.add_api_route(f"{base}/{{item_id}}/status", set_status, methods=["PATCH"], response_model=Out, tags=tag,
                         summary=f"Activate / deactivate {resource.label.lower()} (admin)")


for _resource in RESOURCES.values():
    _register(_resource)


# ------------------------------------------------------------------ hotel room types & seasonal rates
hotels = RESOURCES["hotels"]
hotel_tag = ["Inventory: Hotels"]


def _hotel(db, hotel_id: int) -> Hotel:
    hotel = db.get(Hotel, hotel_id)
    if hotel is None:
        raise DomainError("Hotel not found.", status.HTTP_404_NOT_FOUND, "not_found")
    return hotel


def _child(db, model, hotel_id: int, child_id: int, label: str):
    obj = db.get(model, child_id)
    if obj is None or obj.hotel_id != hotel_id:
        raise DomainError(f"{label} not found for this hotel.", status.HTTP_404_NOT_FOUND, "not_found")
    return obj


@router.post("/hotels/{hotel_id}/room-types", response_model=HotelOut, tags=hotel_tag, summary="Add room type (admin)")
def add_room_type(hotel_id: int, body: RoomTypeIn, db: DB, _: AdminUser):
    hotel = _hotel(db, hotel_id)  # keep a reference: SQLAlchemy needs the parent alive to track the append
    hotel.room_types.append(HotelRoomType(**body.model_dump()))
    db.commit()
    db.expire_all()
    return InventoryService(db, hotels).get(hotel_id)


@router.put("/hotels/{hotel_id}/room-types/{room_type_id}", response_model=HotelOut, tags=hotel_tag, summary="Update room type (admin)")
def update_room_type(hotel_id: int, room_type_id: int, body: RoomTypeIn, db: DB, _: AdminUser):
    rt = _child(db, HotelRoomType, hotel_id, room_type_id, "Room type")
    for k, v in body.model_dump().items():
        setattr(rt, k, v)
    db.commit()
    db.expire_all()
    return InventoryService(db, hotels).get(hotel_id)


@router.delete("/hotels/{hotel_id}/room-types/{room_type_id}", response_model=HotelOut, tags=hotel_tag,
               summary="Delete room type and its seasonal rates (admin)")
def delete_room_type(hotel_id: int, room_type_id: int, db: DB, _: AdminUser):
    db.delete(_child(db, HotelRoomType, hotel_id, room_type_id, "Room type"))
    db.commit()
    db.expire_all()
    return InventoryService(db, hotels).get(hotel_id)


def _check_rate(db, hotel_id: int, body: RateIn) -> None:
    _child(db, HotelRoomType, hotel_id, body.room_type_id, "Room type")


@router.post("/hotels/{hotel_id}/rates", response_model=HotelOut, tags=hotel_tag, summary="Add seasonal rate (admin)")
def add_rate(hotel_id: int, body: RateIn, db: DB, _: AdminUser):
    hotel = _hotel(db, hotel_id)
    _check_rate(db, hotel_id, body)
    hotel.rates.append(HotelRate(**body.model_dump()))
    db.commit()
    db.expire_all()
    return InventoryService(db, hotels).get(hotel_id)


@router.put("/hotels/{hotel_id}/rates/{rate_id}", response_model=HotelOut, tags=hotel_tag, summary="Update seasonal rate (admin)")
def update_rate(hotel_id: int, rate_id: int, body: RateIn, db: DB, _: AdminUser):
    rate = _child(db, HotelRate, hotel_id, rate_id, "Rate")
    _check_rate(db, hotel_id, body)
    for k, v in body.model_dump().items():
        setattr(rate, k, v)
    db.commit()
    db.expire_all()
    return InventoryService(db, hotels).get(hotel_id)


@router.delete("/hotels/{hotel_id}/rates/{rate_id}", response_model=HotelOut, tags=hotel_tag, summary="Delete seasonal rate (admin)")
def delete_rate(hotel_id: int, rate_id: int, db: DB, _: AdminUser):
    db.delete(_child(db, HotelRate, hotel_id, rate_id, "Rate"))
    db.commit()
    db.expire_all()
    return InventoryService(db, hotels).get(hotel_id)
