"""Media library service (PRD Part 12). Extended in Phase 2c."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Media, MediaLink


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
