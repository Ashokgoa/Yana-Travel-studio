"""Housekeeping (Phase 8b): backups, demo data removal (administrators) and itinerary templates (planners)."""

from fastapi import APIRouter, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import DB, AdminUser, CurrentUser
from app.schemas.itinerary import ItinerarySummary
from app.services import itinerary_presenter as present
from app.services.backup_service import BackupService
from app.services.demo_data_service import DemoDataService
from app.services.itinerary_templates import TemplateService

router = APIRouter()


# ------------------------------------------------------------------ backups
@router.get("/admin/backups", tags=["Administration"], summary="Backups, newest first")
def list_backups(_: AdminUser):
    return BackupService().list()


@router.post("/admin/backups", tags=["Administration"], status_code=status.HTTP_201_CREATED,
             summary="Create a backup now (database, uploaded images, generated PDFs)")
def create_backup(user: AdminUser):
    return BackupService().create(created_by=user.email)


@router.get("/admin/backups/{name}/download", tags=["Administration"], response_class=FileResponse, summary="Download a backup")
def download_backup(name: str, _: AdminUser):
    path = BackupService().file(name)
    return FileResponse(path, media_type="application/zip", filename=path.name, headers={"Cache-Control": "no-store"})


@router.delete("/admin/backups/{name}", tags=["Administration"], status_code=status.HTTP_204_NO_CONTENT, summary="Delete a backup")
def delete_backup(name: str, _: AdminUser):
    BackupService().delete(name)


# ------------------------------------------------------------------ demo data
@router.get("/admin/demo-data", tags=["Administration"], summary="How much demonstration inventory is present")
def demo_summary(db: DB, _: AdminUser):
    return DemoDataService(db).summary()


@router.post("/admin/demo-data/remove", tags=["Administration"], summary="Remove demo inventory (records used by itineraries are deactivated)")
def demo_remove(db: DB, _: AdminUser):
    return DemoDataService(db).remove()


# ------------------------------------------------------------------ templates
class TemplateIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class FromTemplateIn(BaseModel):
    template_id: int


@router.get("/itinerary-templates", tags=["Itinerary templates"], response_model=list[ItinerarySummary], summary="Itinerary templates")
def list_templates(db: DB, user: CurrentUser):
    return present.summaries(db, TemplateService(db, user).list())


@router.post("/itineraries/{itinerary_id}/save-as-template", tags=["Itinerary templates"], response_model=ItinerarySummary,
             status_code=status.HTTP_201_CREATED, summary="Save a copy of this itinerary (latest or ?version=) as a template")
def save_as_template(itinerary_id: int, body: TemplateIn, db: DB, user: CurrentUser, version: int | None = None):
    tpl = TemplateService(db, user).save_as_template(itinerary_id, body.title, body.description, version)
    return present.summaries(db, [tpl])[0]


@router.delete("/itinerary-templates/{template_id}", tags=["Itinerary templates"], status_code=status.HTTP_204_NO_CONTENT, summary="Archive a template")
def archive_template(template_id: int, db: DB, user: CurrentUser):
    TemplateService(db, user).archive(template_id)


@router.post("/enquiries/{enquiry_id}/itineraries/from-template", tags=["Itinerary templates"], response_model=ItinerarySummary,
             status_code=status.HTTP_201_CREATED, summary="Start an itinerary for this enquiry from a template (dates moved, rooms re-priced)")
def from_template(enquiry_id: int, body: FromTemplateIn, db: DB, user: CurrentUser):
    it = TemplateService(db, user).use(enquiry_id, body.template_id)
    return present.summaries(db, [it])[0]
