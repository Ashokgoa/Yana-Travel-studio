"""PDF proposals (Phase 6): designer settings, live preview, export and history.

An export is always tied to a saved, read-only version. If the planner exports
while a working draft is open, the draft is saved first as a version named
"PDF proposal", so the PDF can always be traced back to the exact content.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import date

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import DomainError
from app.models import AppSetting, Enquiry, EnquiryStatusHistory, Itinerary, Media, ProposalExport, User
from app.models.enums import EnquiryStatus
from app.schemas.proposal import SECTION_LABELS, TEMPLATES, BrandingSettings, ProposalExportOut, ProposalOptions, ProposalSettings
from app.services.itinerary_checks import evaluate
from app.services.itinerary_editor import ItineraryEditor
from app.services.itinerary_service import ItineraryService
from app.services.proposal_content import ProposalBuilder
from app.services.proposal_render import PdfRenderer, get_pdf_renderer, render_html
from app.services.storage import LocalFileStorage

BRANDING_KEY = "proposal_branding"
TEMPLATE_INFO = {
    "classic": "Clean and simple, like a printed brochure: route map on the first page, days flowing on.",
    "premium": "Full-page photo cover, serif headings and one day per page.",
    "explorer": "Day-by-day timeline with photos beside the text.",
}
# Statuses that move to "Proposal generated" when a PDF is created (later stages are left alone).
ADVANCE_FROM = {EnquiryStatus.NEW, EnquiryStatus.IN_PROGRESS, EnquiryStatus.REVISION_REQUESTED}


def _slug(text: str | None, limit: int = 40) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text[:limit].rstrip("_") or "Proposal"


def proposal_filename(tour: str, customer: str | None, version_number: int) -> str:
    """`YANA_<Tour>_<Customer>_V<n>.pdf` (PRD Phase 6)."""
    parts = ["YANA", _slug(tour)]
    if customer:
        parts.append(_slug(customer, 30))
    return "_".join(parts) + f"_V{version_number}.pdf"


class ProposalService:
    def __init__(self, db: Session, renderer: PdfRenderer | None = None):
        self.db = db
        self.renderer = renderer
        self.itineraries = ItineraryService(db)
        self.exports = LocalFileStorage(get_settings().exports_dir)

    # ----------------------------------------------------------------- branding (admin)
    def branding(self) -> BrandingSettings:
        row = self.db.scalar(select(AppSetting).where(AppSetting.key == BRANDING_KEY))
        return BrandingSettings.model_validate(row.value) if row and isinstance(row.value, dict) else BrandingSettings()

    def save_branding(self, data: BrandingSettings) -> BrandingSettings:
        if data.logo_media_id is not None and self.db.get(Media, data.logo_media_id) is None:
            raise DomainError("The selected logo image no longer exists.", status.HTTP_400_BAD_REQUEST, "invalid_logo")
        row = self.db.scalar(select(AppSetting).where(AppSetting.key == BRANDING_KEY))
        if row is None:
            row = AppSetting(key=BRANDING_KEY, description="YANA branding and PDF proposal defaults")
            self.db.add(row)
        row.value = data.model_dump(mode="json")
        self.db.commit()
        return data

    # ----------------------------------------------------------------- per-itinerary settings
    def settings(self, itinerary_id: int) -> ProposalSettings:
        it = self.itineraries.get(itinerary_id)
        return ProposalSettings.model_validate(it.proposal_settings) if it.proposal_settings else ProposalSettings()

    def save_settings(self, itinerary_id: int, data: ProposalSettings) -> ProposalSettings:
        it = self.itineraries.get(itinerary_id)
        self._check_images(data)
        it.proposal_settings = data.model_dump(mode="json")
        self.db.commit()
        return data

    def _check_images(self, data: ProposalSettings) -> None:
        ids = {m for m in data.day_images.values() if m}
        if ids and len(set(self.db.scalars(select(Media.id).where(Media.id.in_(ids))))) != len(ids):
            raise DomainError("One of the chosen photos no longer exists.", status.HTTP_400_BAD_REQUEST, "invalid_image")

    def options(self, itinerary_id: int, version_number: int | None = None) -> ProposalOptions:
        it = self.itineraries.get(itinerary_id)
        v = self.itineraries.current_version(it, version_number)
        ev = evaluate(self.db, v, it.enquiry_id)
        return ProposalOptions(
            templates=[{"key": k, "label": k.title(), "description": TEMPLATE_INFO[k]} for k in TEMPLATES],
            sections=[{"key": k, "label": label} for k, label in SECTION_LABELS.items()],
            day_images=ProposalBuilder(self.db).image_choices(v),
            internal_estimate_per_person=str(ev.cost_per_person) if ev.cost_per_person else None,
            currency=ev.currency,
        )

    # ----------------------------------------------------------------- preview and export
    def preview_html(self, itinerary_id: int, settings: ProposalSettings | None = None, version_number: int | None = None) -> str:
        it = self.itineraries.get(itinerary_id)
        v = self.itineraries.current_version(it, version_number)
        data = settings or self.settings(itinerary_id)
        self._check_images(data)
        return render_html(ProposalBuilder(self.db).build(it, v, data, self.branding()))

    def export(self, itinerary_id: int, user: User, settings: ProposalSettings | None = None, version_number: int | None = None) -> ProposalExport:
        it = self.itineraries.get(itinerary_id)
        data = settings or self.settings(itinerary_id)
        self._check_images(data)
        if settings is not None:
            it.proposal_settings = data.model_dump(mode="json")

        v = self.itineraries.current_version(it, version_number)
        if not v.is_locked:
            v = ItineraryEditor(self.db, user).save_version(
                itinerary_id, "PDF proposal", f"Saved automatically when the PDF proposal was created on {date.today():%d %b %Y}."
            )
            it = self.itineraries.get(itinerary_id)
            v = self.itineraries.current_version(it, v.version_number)

        html = render_html(ProposalBuilder(self.db).build(it, v, data, self.branding()))
        pdf = (self.renderer or get_pdf_renderer()).render(html)

        enquiry = self.db.scalar(select(Enquiry).options(joinedload(Enquiry.customer)).where(Enquiry.id == it.enquiry_id)) if it.enquiry_id else None
        filename = proposal_filename(data.title or it.title, enquiry.customer.name if enquiry else None, v.version_number)
        key = self.exports.save(f"itineraries/{uuid.uuid4().hex}.pdf", pdf)
        export = ProposalExport(itinerary_id=it.id, version_id=v.id, version_number=v.version_number, file_key=key, filename=filename,
                                template=data.template, branding=data.branding, settings=data.model_dump(mode="json"),
                                size_bytes=len(pdf), created_by_id=user.id)
        self.db.add(export)
        if enquiry and enquiry.status in ADVANCE_FROM:
            enquiry.status_history.append(EnquiryStatusHistory(
                from_status=enquiry.status, to_status=EnquiryStatus.PROPOSAL_GENERATED, changed_by_id=user.id,
                note=f"PDF proposal created: {filename}",
            ))
            enquiry.status = EnquiryStatus.PROPOSAL_GENERATED
        try:
            self.db.commit()
        except Exception:
            self.exports.delete(key)
            raise
        return export

    def history(self, itinerary_id: int) -> list[ProposalExportOut]:
        self.itineraries.get(itinerary_id)
        rows = self.db.scalars(
            select(ProposalExport).options(joinedload(ProposalExport.created_by))
            .where(ProposalExport.itinerary_id == itinerary_id).order_by(ProposalExport.id.desc())
        ).all()
        return [ProposalExportOut.model_validate(r).model_copy(update={"created_by_name": r.created_by.full_name if r.created_by else None})
                for r in rows]

    def file(self, itinerary_id: int, export_id: int) -> tuple[ProposalExport, bytes]:
        export = self.db.get(ProposalExport, export_id)
        if export is None or export.itinerary_id != itinerary_id:
            raise DomainError("PDF not found.", status.HTTP_404_NOT_FOUND, "not_found")
        if not self.exports.exists(export.file_key):
            raise DomainError("The PDF file is missing from the exports folder.", status.HTTP_410_GONE, "file_missing")
        return export, self.exports.read(export.file_key)

    def get_itinerary(self, itinerary_id: int) -> Itinerary:
        return self.itineraries.get(itinerary_id)
