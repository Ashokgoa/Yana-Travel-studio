"""Central image library (PRD Part 12).

`Media` is one stored file (deduplicated by SHA-256). `MediaLink` attaches a
media item to any inventory record, so one photo can be reused in several
places without duplicating the file. Links are polymorphic (entity_type +
entity_id), so integrity is enforced by the media service.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin

MEDIA_ENTITY_TYPES = ("country", "city", "attraction", "hotel", "restaurant", "vehicle", "brand")
MEDIA_SOURCES = ("upload", "supplier", "stock", "ai_generated")


class Media(IdMixin, TimestampMixin, Base):
    __tablename__ = "media"

    storage_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(300))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), default="upload", nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    alt_text: Mapped[str | None] = mapped_column(String(300))
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_illustrative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    links: Mapped[list["MediaLink"]] = relationship(back_populates="media", cascade="all, delete-orphan")


class MediaLink(IdMixin, TimestampMixin, Base):
    __tablename__ = "media_links"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "media_id", name="uq_media_links_entity_media"),
    )

    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    caption: Mapped[str | None] = mapped_column(String(300))

    media: Mapped[Media] = relationship(back_populates="links")
