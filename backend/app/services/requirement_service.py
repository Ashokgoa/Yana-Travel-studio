"""Customer requirement capture (PRD Part 7) and requirement validation (PRD 13.2 step 1).

Every step is saved as a draft. Completeness is *reported* (`missing`) and
conflicts are *flagged* (`warnings`), never silently fixed or discarded.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import DomainError
from app.models import City, Country, Enquiry, EnquiryDestination, EnquiryRequirement, EnquiryStatusHistory, User
from app.models.enums import BudgetBasis, EnquiryStatus
from app.schemas.requirements import DestinationOut, RequirementIn, RequirementOut, RoomLine

ROOM_OCCUPANCY = {"single": 1, "double": 2, "twin": 2, "triple": 3, "family": 4, "suite": 2}


class RequirementService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------- read
    def get(self, enquiry_id: int) -> RequirementOut:
        enquiry = self._enquiry(enquiry_id)
        req = self._load(enquiry_id)
        return self._out(enquiry, req) if req else self._defaults(enquiry)

    # -------------------------------------------------------------- write
    def save(self, enquiry_id: int, data: RequirementIn, user: User) -> RequirementOut:
        enquiry = self._enquiry(enquiry_id)
        self._check_references(data)
        req = self._load(enquiry_id)
        first_save = req is None
        if req is None:
            req = EnquiryRequirement(enquiry_id=enquiry_id)
            self.db.add(req)

        values = data.model_dump(exclude={"destinations", "rooms"})
        for key, value in values.items():
            setattr(req, key, value)
        req.rooms = [r.model_dump() for r in data.rooms]
        req.updated_by_id = user.id
        req.destinations = [
            EnquiryDestination(country_id=d.country_id, city_id=d.city_id, preference=d.preference, min_nights=d.min_nights, sort_order=i)
            for i, d in enumerate(data.destinations)
        ]

        self._sync_enquiry(enquiry, data)
        if first_save and enquiry.status == EnquiryStatus.NEW:
            enquiry.status_history.append(EnquiryStatusHistory(
                from_status=EnquiryStatus.NEW, to_status=EnquiryStatus.IN_PROGRESS, changed_by_id=user.id,
                note="Requirement capture started"))
            enquiry.status = EnquiryStatus.IN_PROGRESS

        self.db.commit()
        self.db.expire_all()
        return self.get(enquiry_id)

    # -------------------------------------------------------------- helpers
    def _enquiry(self, enquiry_id: int) -> Enquiry:
        enquiry = self.db.scalar(
            select(Enquiry).options(joinedload(Enquiry.customer), selectinload(Enquiry.status_history)).where(Enquiry.id == enquiry_id)
        )
        if enquiry is None:
            raise DomainError("Enquiry not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return enquiry

    def _load(self, enquiry_id: int) -> EnquiryRequirement | None:
        return self.db.scalar(
            select(EnquiryRequirement)
            .options(selectinload(EnquiryRequirement.destinations).joinedload(EnquiryDestination.country),
                     selectinload(EnquiryRequirement.destinations).joinedload(EnquiryDestination.city).joinedload(City.country))
            .where(EnquiryRequirement.enquiry_id == enquiry_id)
        )

    def _check_references(self, data: RequirementIn) -> None:
        country_ids = {d.country_id for d in data.destinations} | {c for c in (data.start_country_id, data.end_country_id) if c}
        if country_ids:
            found = set(self.db.scalars(select(Country.id).where(Country.id.in_(country_ids))))
            if found != country_ids:
                raise DomainError("One or more selected countries do not exist.", status.HTTP_400_BAD_REQUEST, "invalid_reference")
        city_ids = {d.city_id for d in data.destinations if d.city_id}
        if city_ids:
            city_country = dict(self.db.execute(select(City.id, City.country_id).where(City.id.in_(city_ids))).all())
            for d in data.destinations:
                if d.city_id is None:
                    continue
                if d.city_id not in city_country:
                    raise DomainError("One or more selected cities do not exist.", status.HTTP_400_BAD_REQUEST, "invalid_reference")
                if city_country[d.city_id] != d.country_id:
                    raise DomainError("A selected city does not belong to the selected country.", status.HTTP_400_BAD_REQUEST, "city_country_mismatch")

    @staticmethod
    def _sync_enquiry(enquiry: Enquiry, data: RequirementIn) -> None:
        """Keep the enquiry summary (list views, dashboard) consistent with the detailed requirements."""
        enquiry.adults, enquiry.children = data.adults, data.children
        if data.arrival_date:
            enquiry.travel_start_date = data.arrival_date
        if data.departure_date:
            enquiry.travel_end_date = data.departure_date
        if data.budget_per_person is not None:
            enquiry.budget_amount, enquiry.budget_basis = data.budget_per_person, BudgetBasis.PER_PERSON
        elif data.budget_total is not None:
            enquiry.budget_amount, enquiry.budget_basis = data.budget_total, BudgetBasis.TOTAL
        enquiry.budget_currency = data.currency

    def _defaults(self, enquiry: Enquiry) -> RequirementOut:
        """Unsaved form, pre-filled from the enquiry and customer."""
        customer_ages = list(enquiry.customer.children_ages or [])
        # Customer ages are only reused when they match this trip's number of children.
        ages = customer_ages if len(customer_ages) == enquiry.children else []
        children = enquiry.children
        per_person = enquiry.budget_amount if enquiry.budget_basis == BudgetBasis.PER_PERSON else None
        total = enquiry.budget_amount if enquiry.budget_basis == BudgetBasis.TOTAL else None
        out = RequirementOut(
            enquiry_id=enquiry.id, exists=False, adults=enquiry.adults, children=children, children_ages=ages,
            arrival_date=enquiry.travel_start_date, departure_date=enquiry.travel_end_date,
            arrival_airport=None, departure_airport=None, start_country_id=None, end_country_id=None,
            travel_type=None, group_size=None, destinations=[], interests=[], travel_pace=None,
            hotel_categories=[], hotel_locations=[], breakfast_required=True, rooms=[], food_preferences=[], meals=["breakfast"],
            transport_modes=[], passenger_capacity=None, luggage_notes=None, airport_transfers=True, local_sightseeing_transport=True,
            budget_per_person=per_person, budget_total=total, currency=enquiry.budget_currency, budget_flexibility=None,
            travel_class=None, additional_requirements=None, internal_notes=None, completed_steps=[],
        )
        return self._analyse(out)

    def _out(self, enquiry: Enquiry, req: EnquiryRequirement) -> RequirementOut:
        out = RequirementOut.model_validate(req).model_copy(update={
            "destinations": [DestinationOut.model_validate(d) for d in req.destinations],
            "rooms": [RoomLine(**r) for r in req.rooms],
        })
        return self._analyse(out)

    @staticmethod
    def _analyse(r: RequirementOut) -> RequirementOut:
        travellers = r.adults + r.children
        days = nights = None
        if r.arrival_date and r.departure_date and r.departure_date >= r.arrival_date:
            nights = (r.departure_date - r.arrival_date).days
            days = nights + 1
        rooms_count = sum(x.count for x in r.rooms)
        capacity = sum(ROOM_OCCUPANCY.get(x.type, 2) * x.count for x in r.rooms)

        visiting = [d for d in r.destinations if d.preference != "avoid"]
        avoided_countries = {d.country.id for d in r.destinations if d.preference == "avoid" and d.city is None}
        missing = []
        if not r.arrival_date:
            missing.append("Arrival date")
        if not r.departure_date:
            missing.append("Departure date")
        if not r.arrival_airport:
            missing.append("Arrival airport / city")
        if not r.departure_airport:
            missing.append("Departure airport / city")
        if not visiting:
            missing.append("At least one destination to visit")

        warnings = []
        # Itinerary first, budget later (YANA, 2026-11-24): costs come from supplier quotes afterwards.
        if r.budget_per_person is None and r.budget_total is None:
            warnings.append("No budget yet: itineraries can be generated; add a budget later to compare costs against it.")
        mandatory = [d for d in r.destinations if d.preference == "mandatory"]
        if nights is not None and nights == 0:
            warnings.append("Arrival and departure are on the same day: there are no overnight stays.")
        if nights is not None and len(mandatory) > max(nights, 0):
            warnings.append(f"{len(mandatory)} must-visit destinations but only {nights} nights: they cannot all have an overnight stay.")
        min_total = sum(d.min_nights or 0 for d in visiting)
        if nights is not None and min_total > nights:
            warnings.append(f"Minimum nights requested ({min_total}) exceed the {nights} nights available.")
        for label, cid in (("Starting", r.start_country_id), ("Ending", r.end_country_id)):
            if cid and cid in avoided_countries:
                warnings.append(f"{label} country is also marked as a country to avoid.")
        for d in r.destinations:
            if d.city and d.preference != "avoid" and d.country.id in avoided_countries:
                warnings.append(f"{d.city.name} is in {d.country.name}, which is marked as a country to avoid.")
        if r.rooms and capacity < travellers:
            warnings.append(f"Rooms sleep {capacity} but there are {travellers} travellers.")
        if r.passenger_capacity and r.passenger_capacity < travellers:
            warnings.append(f"Vehicle capacity ({r.passenger_capacity}) is less than the number of travellers ({travellers}).")
        if r.group_size and r.group_size < travellers:
            warnings.append(f"Group size ({r.group_size}) is smaller than the number of travellers ({travellers}).")
        if r.budget_per_person and r.budget_total and travellers:
            implied = r.budget_per_person * travellers
            if abs(implied - r.budget_total) > r.budget_total * Decimal("0.1"):
                warnings.append(f"Budget per person × {travellers} travellers ({implied:,.0f}) does not match the group total ({r.budget_total:,.0f}).")
        if "indian_jain" in r.food_preferences:
            warnings.append("Jain food: only restaurants with verified Jain availability will be suggested.")

        return r.model_copy(update={
            "total_days": days, "total_nights": nights, "total_travellers": travellers,
            "rooms_count": rooms_count, "room_capacity": capacity,
            "missing": missing, "warnings": warnings, "is_complete": not missing,
        })
