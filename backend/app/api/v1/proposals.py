"""PDF proposals (Phase 6): designer settings, live preview, export and download."""

from fastapi import APIRouter, Response, status

from app.api.deps import DB, AdminUser, CurrentUser
from app.schemas.proposal import BrandingSettings, ProposalExportOut, ProposalOptions, ProposalSettings
from app.services.proposal_service import ProposalService

router = APIRouter(tags=["PDF proposals"])

# The preview is static HTML with embedded images only: no scripts, no external requests.
PREVIEW_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:; frame-ancestors 'self'"


@router.get("/itineraries/{itinerary_id}/proposal/settings", response_model=ProposalSettings, summary="PDF designer settings")
def get_settings(itinerary_id: int, db: DB, _: CurrentUser):
    return ProposalService(db).settings(itinerary_id)


@router.put("/itineraries/{itinerary_id}/proposal/settings", response_model=ProposalSettings, summary="Save PDF designer settings")
def save_settings(itinerary_id: int, body: ProposalSettings, db: DB, _: CurrentUser):
    return ProposalService(db).save_settings(itinerary_id, body)


@router.get("/itineraries/{itinerary_id}/proposal/options", response_model=ProposalOptions,
            summary="Templates, sections and per-day photo choices for the designer")
def options(itinerary_id: int, db: DB, _: CurrentUser, version: int | None = None):
    return ProposalService(db).options(itinerary_id, version)


@router.post("/itineraries/{itinerary_id}/proposal/preview", response_class=Response,
             summary="Live preview (HTML) with the given settings; nothing is saved")
def preview(itinerary_id: int, db: DB, _: CurrentUser, body: ProposalSettings | None = None, version: int | None = None):
    html = ProposalService(db).preview_html(itinerary_id, body, version)
    return Response(content=html, media_type="text/html; charset=utf-8", headers={
        "Content-Security-Policy": PREVIEW_CSP, "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
    })


@router.post("/itineraries/{itinerary_id}/proposal/export", response_model=ProposalExportOut, status_code=status.HTTP_201_CREATED,
             summary="Create the PDF (saves an open draft as a version first) and record it")
def export(itinerary_id: int, db: DB, user: CurrentUser, body: ProposalSettings | None = None, version: int | None = None):
    service = ProposalService(db)
    created = service.export(itinerary_id, user, body, version)
    return next(e for e in service.history(itinerary_id) if e.id == created.id)


@router.get("/itineraries/{itinerary_id}/proposal/exports", response_model=list[ProposalExportOut], summary="PDFs created for this itinerary")
def exports(itinerary_id: int, db: DB, _: CurrentUser):
    return ProposalService(db).history(itinerary_id)


@router.get("/itineraries/{itinerary_id}/proposal/exports/{export_id}/file", response_class=Response, summary="Download a PDF")
def download(itinerary_id: int, export_id: int, db: DB, _: CurrentUser):
    export, data = ProposalService(db).file(itinerary_id, export_id)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{export.filename}"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
    })


@router.get("/settings/branding", response_model=BrandingSettings, summary="YANA branding and PDF defaults")
def get_branding(db: DB, _: CurrentUser):
    return ProposalService(db).branding()


@router.put("/settings/branding", response_model=BrandingSettings, summary="Update YANA branding and PDF defaults (administrators)")
def save_branding(body: BrandingSettings, db: DB, _: AdminUser):
    return ProposalService(db).save_branding(body)
