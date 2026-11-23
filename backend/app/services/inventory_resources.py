"""Declarations of every inventory resource served by the generic CRUD service."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Attraction,
    City,
    Country,
    Hotel,
    Restaurant,
    Supplier,
    Vehicle,
    VehicleCategory,
)
from app.schemas import inventory as s
from app.services.inventory_service import Filter, Resource, eq, is_true

_city_with_country = joinedload(Attraction.city).joinedload(City.country)


def _country_city_counts(db: Session, rows: list) -> dict[int, dict]:
    ids = [r.id for r in rows]
    counts = dict(db.execute(select(City.country_id, func.count()).where(City.country_id.in_(ids)).group_by(City.country_id)).all())
    return {i: {"city_count": counts.get(i, 0)} for i in ids}


def _vehicle_columns(db: Session, data: s.VehicleIn) -> dict:
    cols = data.model_dump(exclude={"operating_country_ids"})
    ids = list(dict.fromkeys(data.operating_country_ids))
    countries = list(db.scalars(select(Country).where(Country.id.in_(ids)))) if ids else []
    if len(countries) != len(ids):
        from fastapi import status

        from app.core.errors import DomainError

        raise DomainError("One or more operating countries do not exist.", status.HTTP_400_BAD_REQUEST, "invalid_reference")
    cols["operating_countries"] = countries
    return cols


def _in_country(city_fk):
    """Filter rows whose city belongs to the given country (rows joined to City)."""
    return Filter(int, lambda stmt, v: stmt.where(City.country_id == v))


RESOURCES: dict[str, Resource] = {
    "countries": Resource(
        name="countries", label="Country", model=Country, schema_in=s.CountryIn, schema_out=s.CountryOut,
        search_columns=[Country.name, Country.iso_code, Country.region],
        filters={"region": eq(Country.region, str)},
        order_by=[Country.sort_order, Country.name],
        entity_type="country",
        enrich=_country_city_counts,
        duplicate_message="A country with this name or ISO code already exists.",
    ),
    "cities": Resource(
        name="cities", label="City", model=City, schema_in=s.CityIn, schema_out=s.CityOut,
        search_columns=[City.name],
        filters={"country_id": eq(City.country_id)},
        order_by=[City.name],
        load_options=[joinedload(City.country)],
        references={"country_id": (Country, "country")},
        entity_type="city",
        duplicate_message="This country already has a city with that name.",
    ),
    "suppliers": Resource(
        name="suppliers", label="Supplier", model=Supplier, schema_in=s.SupplierIn, schema_out=s.SupplierOut,
        search_columns=[Supplier.name, Supplier.contact_name, Supplier.email],
        filters={"supplier_type": eq(Supplier.supplier_type, str), "country_id": eq(Supplier.country_id)},
        order_by=[Supplier.name],
        load_options=[joinedload(Supplier.country)],
        references={"country_id": (Country, "country")},
    ),
    "attractions": Resource(
        name="attractions", label="Attraction", model=Attraction, schema_in=s.AttractionIn, schema_out=s.AttractionOut,
        search_columns=[Attraction.name, City.name],
        filters={
            "city_id": eq(Attraction.city_id),
            "country_id": _in_country(Attraction.city_id),
            "category": eq(Attraction.category, str),
            "child_friendly": is_true(Attraction.child_friendly),
        },
        order_by=[City.name, Attraction.name],
        joins=[Attraction.city],
        load_options=[_city_with_country, joinedload(Attraction.supplier)],
        references={"city_id": (City, "city"), "supplier_id": (Supplier, "supplier")},
        entity_type="attraction",
    ),
    "hotels": Resource(
        name="hotels", label="Hotel", model=Hotel, schema_in=s.HotelIn, schema_out=s.HotelOut,
        search_columns=[Hotel.name, City.name],
        filters={
            "city_id": eq(Hotel.city_id),
            "country_id": _in_country(Hotel.city_id),
            "star_rating": eq(Hotel.star_rating),
        },
        order_by=[City.name, Hotel.name],
        joins=[Hotel.city],
        load_options=[
            joinedload(Hotel.city).joinedload(City.country),
            joinedload(Hotel.supplier),
            selectinload(Hotel.room_types),
            selectinload(Hotel.rates),
        ],
        references={"city_id": (City, "city"), "supplier_id": (Supplier, "supplier")},
        entity_type="hotel",
    ),
    "restaurants": Resource(
        name="restaurants", label="Restaurant", model=Restaurant, schema_in=s.RestaurantIn, schema_out=s.RestaurantOut,
        search_columns=[Restaurant.name, Restaurant.cuisine, City.name],
        filters={
            "city_id": eq(Restaurant.city_id),
            "country_id": _in_country(Restaurant.city_id),
            "vegetarian": is_true(Restaurant.vegetarian),
            "jain": is_true(Restaurant.jain),
            "halal": is_true(Restaurant.halal),
            "vegan": is_true(Restaurant.vegan),
        },
        order_by=[City.name, Restaurant.name],
        joins=[Restaurant.city],
        load_options=[joinedload(Restaurant.city).joinedload(City.country), joinedload(Restaurant.supplier)],
        references={"city_id": (City, "city"), "supplier_id": (Supplier, "supplier")},
        entity_type="restaurant",
    ),
    "vehicles": Resource(
        name="vehicles", label="Vehicle", model=Vehicle, schema_in=s.VehicleIn, schema_out=s.VehicleOut,
        search_columns=[Vehicle.name],
        filters={"category_id": eq(Vehicle.category_id), "supplier_id": eq(Vehicle.supplier_id)},
        order_by=[Vehicle.passenger_capacity, Vehicle.name],
        load_options=[joinedload(Vehicle.category), joinedload(Vehicle.supplier), selectinload(Vehicle.operating_countries)],
        references={"category_id": (VehicleCategory, "vehicle category"), "supplier_id": (Supplier, "supplier")},
        entity_type="vehicle",
        to_columns=_vehicle_columns,
    ),
}
