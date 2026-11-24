"""Itinerary templates (Phase 8b, PRD: "itinerary templates, e.g. a 12-day Grand Tour; not hardcoded").

A template is an itinerary with kind="template" and no enquiry: a saved, read-only
copy of a planner's itinerary. Using a template for an enquiry copies it as a new
proposal, moves the dates to the customer's arrival date and re-prices the hotel
rooms for the new dates (season rates), so nothing is hardcoded and every template
comes from real, reviewed work.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError
from app.models import Enquiry, Hotel, Itinerary, User
from app.services.itinerary_editor import ItineraryEditor
from app.services.itinerary_service import ItineraryService
from app.services.requirement_service import RequirementService


class TemplateService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.editor = ItineraryEditor(db, user)
        self.itineraries = ItineraryService(db)

    def save_as_template(self, itinerary_id: int, title: str, description: str | None, version_number: int | None = None) -> Itinerary:
        src_it = self.itineraries.get(itinerary_id)
        src = self.itineraries.current_version(src_it, version_number)
        tpl = Itinerary(enquiry_id=None, kind="template", title=title.strip()[:200], strategy=src_it.strategy, status="template",
                        batch=1, created_by_id=self.user.id, proposal_settings=deepcopy(src_it.proposal_settings))
        self.db.add(tpl)
        self.db.flush()
        v = self.editor._clone(src, tpl, label="Template", notes=description or f"Saved from itinerary #{src_it.id}, version {src.version_number}", number=1)
        v.is_locked = True
        self.db.commit()
        return self.itineraries.get(tpl.id)

    def list(self) -> list[Itinerary]:
        return list(self.db.scalars(select(Itinerary).options(selectinload(Itinerary.versions))
                                    .where(Itinerary.kind == "template", Itinerary.is_archived.is_(False))
                                    .order_by(Itinerary.title, Itinerary.id)))

    def _template(self, template_id: int) -> Itinerary:
        tpl = self.itineraries.get(template_id)
        if tpl.kind != "template" or tpl.is_archived:
            raise DomainError("Template not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return tpl

    def archive(self, template_id: int) -> None:
        self._template(template_id).is_archived = True
        self.db.commit()

    def use(self, enquiry_id: int, template_id: int) -> Itinerary:
        enquiry = self.db.get(Enquiry, enquiry_id)
        if enquiry is None:
            raise DomainError("Enquiry not found.", status.HTTP_404_NOT_FOUND, "not_found")
        tpl = self._template(template_id)
        src = self.itineraries.current_version(tpl)
        batch = (self.db.scalar(select(func.max(Itinerary.batch)).where(Itinerary.enquiry_id == enquiry_id)) or 0) + 1
        it = Itinerary(enquiry_id=enquiry_id, kind="proposal", title=tpl.title, strategy=tpl.strategy, batch=batch, created_by_id=self.user.id,
                       proposal_settings=deepcopy(tpl.proposal_settings))  # the template's PDF texts and photos come along
        self.db.add(it)
        self.db.flush()
        v = self.editor._clone(src, it, label="Generated", notes=f"From template “{tpl.title}”", number=1)

        # Move the dates to the customer's arrival date.
        req = RequirementService(self.db).get(enquiry_id)
        start = req.arrival_date or enquiry.travel_start_date
        if start and start != v.start_date:
            delta = timedelta(days=(start - v.start_date).days)
            v.start_date = start
            for d in v.days:
                d.date = d.date + delta
        # Re-price rooms for the new dates (seasonal rates); unknown prices stay unknown.
        for s in v.stays:
            if not s.hotel_id:
                continue
            hotel = self.db.scalar(select(Hotel).options(selectinload(Hotel.room_types), selectinload(Hotel.rates)).where(Hotel.id == s.hotel_id))
            check_in = next((d.date for d in v.days if d.day_number == s.check_in_day), v.start_date)
            if hotel:
                s.rooms = self.editor._map_rooms(hotel, s.rooms, check_in)
                s.estimated_cost = self.editor._stay_cost(s)
        v.is_locked = True
        self.db.commit()
        return self.itineraries.get(it.id)
