from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.models import Attraction, Country, Hotel, Restaurant, Vehicle
from app.seed.demo_inventory import inventory_is_empty, load_demo_inventory
from tests.conftest import alembic_config


def test_demo_seed_loads_into_fresh_database_and_is_labelled(tmp_path):
    url = f"sqlite:///{(tmp_path / 'seed.db').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    with Session(engine) as db:
        assert inventory_is_empty(db)
        counts = load_demo_inventory(db)
        assert counts["countries"] == 8 and not inventory_is_empty(db)
        # PRD Part 21: fictional records are flagged; real attractions are not.
        assert db.scalar(select(func.count()).select_from(Hotel).where(Hotel.is_demo.is_(False))) == 0
        assert db.scalar(select(func.count()).select_from(Restaurant).where(Restaurant.is_demo.is_(False))) == 0
        assert db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.is_demo.is_(False))) == 0
        assert all("(Demo)" in h.name for h in db.scalars(select(Hotel)))
        # Never invent ticket prices or opening hours for real attractions.
        assert db.scalar(select(func.count()).select_from(Attraction).where(Attraction.ticket_price.is_not(None))) == 0
        assert db.scalar(select(func.count()).select_from(Attraction).where(Attraction.opening_hours.is_not(None))) == 0
        # Every hotel price is unverified (shown as estimated).
        assert all(not rt.price_is_verified for h in db.scalars(select(Hotel)) for rt in h.room_types)
        assert {c.iso_code for c in db.scalars(select(Country))} == {"NL", "BE", "FR", "LU", "DE", "CH", "AT", "IT"}
    engine.dispose()
