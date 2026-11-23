"""Image library endpoints (PRD Part 12).

View and library uploads: any signed-in user (planners need photos for proposals).
Inventory galleries, metadata edits, replace and delete: administrators only.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.api.deps import DB, AdminUser, CurrentUser, Pagination
from app.core.config import get_settings
from app.core.errors import DomainError

from app.schemas.common import Page
from app.schemas.media import (
    CaptionBody,
    Category,
    EntityType,
    GalleryItem,
    LinkCreate,
    MediaDetail,
    MediaOut,
    MediaUpdate,
    ReorderBody,
    Source,
    UploadResult,
    Usage,
)
from app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["Image library"])


async def _read_limited(file: UploadFile) -> bytes:
    limit = get_settings().max_upload_mb * 1_048_576
    data = await file.read(limit + 1)  # never read more than the limit into memory
    if len(data) > limit:
        raise DomainError(f"The file is too large. Maximum is {get_settings().max_upload_mb} MB.",
                          status.HTTP_413_CONTENT_TOO_LARGE, "file_too_large")
    return data


def _with_usage(service: MediaService, items) -> list[MediaOut]:
    counts = service.usage_counts([m.id for m in items])
    return [MediaOut.model_validate(m).model_copy(update={"usage_count": counts.get(m.id, 0)}) for m in items]


@router.get("", response_model=Page[MediaOut], summary="Browse the image library")
def list_media(db: DB, _: CurrentUser, page: Pagination, q: str | None = None, category: Category | None = None,
               illustrative: bool | None = None):
    service = MediaService(db)
    items, total = service.list(q, category, illustrative, page.offset, page.page_size)
    return Page(items=_with_usage(service, items), total=total, page=page.page, page_size=page.page_size)


@router.post("/upload", response_model=UploadResult, status_code=status.HTTP_201_CREATED,
             summary="Upload an image (optionally straight into a record's gallery)")
async def upload(
    db: DB,
    user: CurrentUser,
    file: Annotated[UploadFile, File(description="JPG, PNG or WEBP")],
    category: Annotated[Category, Form()] = "library",
    entity_type: Annotated[EntityType | None, Form()] = None,
    entity_id: Annotated[int | None, Form()] = None,
    description: Annotated[str | None, Form(max_length=1000)] = None,
    source: Annotated[Source, Form()] = "upload",
    is_illustrative: Annotated[bool, Form()] = False,
    is_ai_generated: Annotated[bool, Form()] = False,
):
    linking = entity_type is not None or entity_id is not None
    if linking and user.role.code != "admin":
        raise DomainError("Only administrators can change inventory photos.", status.HTTP_403_FORBIDDEN, "forbidden")
    if linking and (entity_type is None or entity_id is None):
        raise DomainError("Provide both entity_type and entity_id.", status.HTTP_400_BAD_REQUEST, "invalid_entity")
    raw = await _read_limited(file)
    service = MediaService(db)
    media, created = service.upload(
        raw, file.filename or "image", category=entity_type or category, user=user,
        description=(description or None), source=source, is_illustrative=is_illustrative, is_ai_generated=is_ai_generated,
    )
    link_id = None
    if linking:
        gallery = service.gallery(entity_type, entity_id)
        existing = next((l for l in gallery if l.media_id == media.id), None)
        if existing is None:
            gallery = service.link(entity_type, entity_id, media.id)
            existing = next(l for l in gallery if l.media_id == media.id)
        link_id = existing.id
    return UploadResult(media=_with_usage(service, [media])[0], created=created, link_id=link_id)


@router.get("/gallery/{entity_type}/{entity_id}", response_model=list[GalleryItem], summary="Images of one record, in order")
def gallery(entity_type: EntityType, entity_id: int, db: DB, _: CurrentUser):
    return MediaService(db).gallery(entity_type, entity_id)


@router.post("/links", response_model=list[GalleryItem], summary="Reuse a library image in a record's gallery (admin)")
def link(body: LinkCreate, db: DB, _: AdminUser):
    return MediaService(db).link(body.entity_type, body.entity_id, body.media_id, body.caption)


@router.delete("/links/{link_id}", response_model=list[GalleryItem], summary="Remove an image from a gallery (admin; file stays in library)")
def unlink(link_id: int, db: DB, _: AdminUser):
    return MediaService(db).unlink(link_id)


@router.post("/links/{link_id}/primary", response_model=list[GalleryItem], summary="Make this the primary image (admin)")
def set_primary(link_id: int, db: DB, _: AdminUser):
    return MediaService(db).set_primary(link_id)


@router.put("/links/{link_id}/caption", response_model=list[GalleryItem], summary="Set the caption shown with this image (admin)")
def caption(link_id: int, body: CaptionBody, db: DB, _: AdminUser):
    return MediaService(db).update_caption(link_id, body.caption)


@router.put("/gallery/{entity_type}/{entity_id}/order", response_model=list[GalleryItem], summary="Reorder a gallery (admin)")
def reorder(entity_type: EntityType, entity_id: int, body: ReorderBody, db: DB, _: AdminUser):
    return MediaService(db).reorder(entity_type, entity_id, body.link_ids)


@router.get("/{media_id}", response_model=MediaDetail, summary="Image details and where it is used")
def get_media(media_id: int, db: DB, _: CurrentUser):
    service = MediaService(db)
    media = service.get(media_id)
    usages = [Usage(**u) for u in service.usages(media)]
    return MediaDetail.model_validate(media).model_copy(update={"usages": usages, "usage_count": len(usages)})


@router.patch("/{media_id}", response_model=MediaOut, summary="Edit description, alt text, source, illustrative flag (admin)")
def update_media(media_id: int, body: MediaUpdate, db: DB, _: AdminUser):
    service = MediaService(db)
    return _with_usage(service, [service.update(media_id, **body.model_dump(exclude_unset=True))])[0]


@router.post("/{media_id}/replace", response_model=MediaOut, summary="Replace the file, keeping every place it is used (admin)")
async def replace(media_id: int, db: DB, _: AdminUser, file: Annotated[UploadFile, File()]):
    raw = await _read_limited(file)
    service = MediaService(db)
    return _with_usage(service, [service.replace(media_id, raw, file.filename or "image")])[0]


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an image everywhere (admin)")
def delete_media(media_id: int, db: DB, _: AdminUser):
    MediaService(db).delete(media_id)


def _file_response(db, media_id: int, thumbnail: bool) -> Response:
    service = MediaService(db)
    media = service.get(media_id)
    data = service.read(media, thumbnail)
    mime = "image/jpeg" if thumbnail and media.thumbnail_key else media.mime_type
    # URLs carry ?v=<hash>, so a changed file always gets a new URL: safe to cache for long.
    return Response(content=data, media_type=mime, headers={
        "Cache-Control": "private, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
    })


@router.get("/{media_id}/file", summary="Image file", response_class=Response)
def media_file(media_id: int, db: DB, _: CurrentUser):
    return _file_response(db, media_id, thumbnail=False)


@router.get("/{media_id}/thumbnail", summary="Thumbnail (JPEG)", response_class=Response)
def media_thumbnail(media_id: int, db: DB, _: CurrentUser):
    return _file_response(db, media_id, thumbnail=True)



