"""Central image library (PRD Part 12).

Files are stored through the storage abstraction under `<folder>/<uuid>.<ext>`
with a JPEG thumbnail beside them. Identical uploads (same SHA-256 of the
original bytes) are stored once and simply re-linked. A `MediaLink` attaches
an image to any inventory record; one image can serve many records.
"""

from __future__ import annotations

import hashlib
import uuid

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.models import Attraction, City, Country, Hotel, Media, MediaLink, Restaurant, User, Vehicle
from app.services.storage import FileStorage, get_storage
from app.utils.images import ImageError, process_image

ENTITY_MODELS = {
    "country": Country,
    "city": City,
    "attraction": Attraction,
    "hotel": Hotel,
    "restaurant": Restaurant,
    "vehicle": Vehicle,
}
FOLDER_FOR = {
    "country": "countries",
    "city": "cities",
    "attraction": "sightseeing",
    "hotel": "hotels",
    "restaurant": "restaurants",
    "vehicle": "transportation",
    "brand": "logo",
    "library": "library",
}


def media_file_url(media: Media, thumbnail: bool = False) -> str:
    # Same-origin path (proxied by Next.js); `v` busts caches when a file is replaced.
    kind = "thumbnail" if thumbnail and media.thumbnail_key else "file"
    return f"/api/v1/media/{media.id}/{kind}?v={media.sha256[:12]}"


def primary_image_urls(db: Session, entity_type: str, entity_ids: list[int]) -> dict[int, str]:
    """Thumbnail URL of each entity's primary image (falls back to its first image)."""
    if not entity_ids:
        return {}
    rows = db.execute(
        select(MediaLink.entity_id, Media)
        .join(Media, Media.id == MediaLink.media_id)
        .where(MediaLink.entity_type == entity_type, MediaLink.entity_id.in_(entity_ids))
        .order_by(MediaLink.entity_id, MediaLink.is_primary.desc(), MediaLink.sort_order, MediaLink.id)
    ).all()
    result: dict[int, str] = {}
    for entity_id, media in rows:
        result.setdefault(entity_id, media_file_url(media, thumbnail=True))
    return result


def _not_found(what: str = "Image") -> DomainError:
    return DomainError(f"{what} not found.", status.HTTP_404_NOT_FOUND, "not_found")


class MediaService:
    def __init__(self, db: Session, storage: FileStorage | None = None):
        self.db = db
        self.storage = storage or get_storage()
        self.max_bytes = get_settings().max_upload_mb * 1_048_576

    # -------------------------------------------------------------- library
    def get(self, media_id: int) -> Media:
        media = self.db.get(Media, media_id)
        if media is None:
            raise _not_found()
        return media

    def list(self, q: str | None, category: str | None, illustrative: bool | None, offset: int, limit: int):
        stmt = select(Media).order_by(Media.created_at.desc(), Media.id.desc())
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(Media.description.ilike(like) | Media.original_filename.ilike(like) | Media.alt_text.ilike(like))
        if category:
            stmt = stmt.where(Media.category == category)
        if illustrative is not None:
            stmt = stmt.where(Media.is_illustrative.is_(illustrative))
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        return list(self.db.scalars(stmt.offset(offset).limit(limit))), total

    def usage_counts(self, media_ids: list[int]) -> dict[int, int]:
        if not media_ids:
            return {}
        return dict(self.db.execute(
            select(MediaLink.media_id, func.count()).where(MediaLink.media_id.in_(media_ids)).group_by(MediaLink.media_id)
        ).all())

    def usages(self, media: Media) -> list[dict]:
        out = []
        for link in sorted(media.links, key=lambda l: (l.entity_type, l.entity_id)):
            model = ENTITY_MODELS.get(link.entity_type)
            entity = self.db.get(model, link.entity_id) if model else None
            out.append({"link_id": link.id, "entity_type": link.entity_type, "entity_id": link.entity_id,
                        "entity_name": getattr(entity, "name", None), "is_primary": link.is_primary})
        return out

    def upload(self, raw: bytes, filename: str, *, category: str, user: User, description: str | None = None,
               alt_text: str | None = None, source: str = "upload", is_illustrative: bool = False,
               is_ai_generated: bool = False) -> tuple[Media, bool]:
        """Returns (media, created). An identical existing file is reused, not stored twice."""
        if category not in FOLDER_FOR:
            raise DomainError("Unknown image category.", status.HTTP_400_BAD_REQUEST, "invalid_category")
        digest = hashlib.sha256(raw).hexdigest()
        existing = self.db.scalar(select(Media).where(Media.sha256 == digest))
        if existing:
            return existing, False
        image = self._process(raw)
        storage_key, thumb_key = self._store(image, FOLDER_FOR[category])
        media = Media(
            storage_key=storage_key, thumbnail_key=thumb_key, original_filename=_safe_display_name(filename),
            mime_type=image.mime_type, size_bytes=len(image.data), width=image.width, height=image.height,
            sha256=digest, category=category, source=source, description=description, alt_text=alt_text,
            # AI images are always illustrative: never presented as a real property (PRD 12.2).
            is_ai_generated=is_ai_generated, is_illustrative=is_illustrative or is_ai_generated, uploaded_by_id=user.id,
        )
        self.db.add(media)
        self.db.commit()
        return media, True

    def update(self, media_id: int, **fields) -> Media:
        media = self.get(media_id)
        for key, value in fields.items():
            if value is not None or key in ("description", "alt_text"):
                setattr(media, key, value)
        if media.is_ai_generated:
            media.is_illustrative = True
        self.db.commit()
        return media

    def replace(self, media_id: int, raw: bytes, filename: str) -> Media:
        """Swap the file of an image, keeping every place it is used (PRD 9.1 'replace')."""
        media = self.get(media_id)
        digest = hashlib.sha256(raw).hexdigest()
        clash = self.db.scalar(select(Media).where(Media.sha256 == digest, Media.id != media.id))
        if clash:
            raise DomainError(f"This exact image is already in the library (image #{clash.id}). Link that one instead.",
                              status.HTTP_409_CONFLICT, "duplicate_image")
        image = self._process(raw)
        old_keys = [media.storage_key, media.thumbnail_key]
        folder = media.storage_key.split("/", 1)[0]
        media.storage_key, media.thumbnail_key = self._store(image, folder)
        media.original_filename = _safe_display_name(filename)
        media.mime_type, media.size_bytes = image.mime_type, len(image.data)
        media.width, media.height, media.sha256 = image.width, image.height, digest
        self.db.commit()
        self._delete_files(old_keys)
        return media

    def delete(self, media_id: int) -> None:
        media = self.get(media_id)
        keys = [media.storage_key, media.thumbnail_key]
        affected = {(l.entity_type, l.entity_id) for l in media.links if l.is_primary}
        self.db.delete(media)  # links cascade
        self.db.flush()
        for entity_type, entity_id in affected:
            self._ensure_primary(entity_type, entity_id)
        self.db.commit()
        self._delete_files(keys)

    def read(self, media: Media, thumbnail: bool) -> bytes:
        key = media.thumbnail_key if thumbnail and media.thumbnail_key else media.storage_key
        try:
            return self.storage.read(key)
        except FileNotFoundError:
            raise DomainError("The image file is missing from storage.", status.HTTP_404_NOT_FOUND, "file_missing")

    # -------------------------------------------------------------- links (gallery of a record)
    def gallery(self, entity_type: str, entity_id: int) -> list[MediaLink]:
        self._check_entity(entity_type, entity_id)
        return list(self.db.scalars(
            select(MediaLink).where(MediaLink.entity_type == entity_type, MediaLink.entity_id == entity_id)
            .order_by(MediaLink.sort_order, MediaLink.id)
        ))

    def link(self, entity_type: str, entity_id: int, media_id: int, caption: str | None = None) -> list[MediaLink]:
        self._check_entity(entity_type, entity_id)
        self.get(media_id)
        current = self.gallery(entity_type, entity_id)
        if any(l.media_id == media_id for l in current):
            raise DomainError("This image is already in this gallery.", status.HTTP_409_CONFLICT, "already_linked")
        self.db.add(MediaLink(media_id=media_id, entity_type=entity_type, entity_id=entity_id, caption=caption,
                              sort_order=(max((l.sort_order for l in current), default=-1) + 1),
                              is_primary=not current))  # first image becomes the primary
        self.db.commit()
        return self.gallery(entity_type, entity_id)

    def unlink(self, link_id: int) -> list[MediaLink]:
        link = self._get_link(link_id)
        entity_type, entity_id = link.entity_type, link.entity_id
        self.db.delete(link)
        self.db.flush()
        self._ensure_primary(entity_type, entity_id)
        self.db.commit()
        return self.gallery(entity_type, entity_id)

    def set_primary(self, link_id: int) -> list[MediaLink]:
        link = self._get_link(link_id)
        for other in self.gallery(link.entity_type, link.entity_id):
            other.is_primary = other.id == link.id
        self.db.commit()
        return self.gallery(link.entity_type, link.entity_id)

    def update_caption(self, link_id: int, caption: str | None) -> list[MediaLink]:
        link = self._get_link(link_id)
        link.caption = caption
        self.db.commit()
        return self.gallery(link.entity_type, link.entity_id)

    def reorder(self, entity_type: str, entity_id: int, link_ids: list[int]) -> list[MediaLink]:
        current = self.gallery(entity_type, entity_id)
        if sorted(link_ids) != sorted(l.id for l in current):
            raise DomainError("The new order must list every image of this gallery exactly once.",
                              status.HTTP_400_BAD_REQUEST, "invalid_order")
        position = {lid: i for i, lid in enumerate(link_ids)}
        for link in current:
            link.sort_order = position[link.id]
        self.db.commit()
        return self.gallery(entity_type, entity_id)

    # -------------------------------------------------------------- helpers
    def _process(self, raw: bytes):
        try:
            return process_image(raw, self.max_bytes)
        except ImageError as exc:
            raise DomainError(str(exc), status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_image")

    def _store(self, image, folder: str) -> tuple[str, str]:
        name = uuid.uuid4().hex
        key = self.storage.save(f"{folder}/{name}.{image.extension}", image.data)
        thumb = self.storage.save(f"{folder}/thumbs/{name}.jpg", image.thumbnail)
        return key, thumb

    def _delete_files(self, keys: list[str | None]) -> None:
        for key in keys:
            if key:
                self.storage.delete(key)

    def _check_entity(self, entity_type: str, entity_id: int) -> None:
        model = ENTITY_MODELS.get(entity_type)
        if model is None:
            raise DomainError("Images can't be attached to this kind of record.", status.HTTP_400_BAD_REQUEST, "invalid_entity")
        if self.db.get(model, entity_id) is None:
            raise _not_found("Record")

    def _get_link(self, link_id: int) -> MediaLink:
        link = self.db.get(MediaLink, link_id)
        if link is None:
            raise _not_found("Gallery image")
        return link

    def _ensure_primary(self, entity_type: str, entity_id: int) -> None:
        links = list(self.db.scalars(
            select(MediaLink).where(MediaLink.entity_type == entity_type, MediaLink.entity_id == entity_id)
            .order_by(MediaLink.sort_order, MediaLink.id)
        ))
        if links and not any(l.is_primary for l in links):
            links[0].is_primary = True


def _safe_display_name(filename: str) -> str:
    """Original name is kept for display only (never used as a path)."""
    name = (filename or "image").replace("\\", "/").split("/")[-1]
    return name[:200] or "image"
