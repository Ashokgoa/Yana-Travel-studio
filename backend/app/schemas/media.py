from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from app.schemas.common import OptStr, ORMModel

EntityType = Literal["country", "city", "attraction", "hotel", "restaurant", "vehicle"]
Category = Literal["country", "city", "attraction", "hotel", "restaurant", "vehicle", "brand", "library"]
Source = Literal["upload", "supplier", "stock", "ai_generated"]


class MediaOut(ORMModel):
    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    category: str
    source: str
    description: str | None
    alt_text: str | None
    is_ai_generated: bool
    is_illustrative: bool
    created_at: datetime
    sha256: str = Field(exclude=True)
    thumbnail_key: str | None = Field(default=None, exclude=True)
    usage_count: int = 0

    @computed_field
    @property
    def url(self) -> str:
        return f"/api/v1/media/{self.id}/file?v={self.sha256[:12]}"

    @computed_field
    @property
    def thumbnail_url(self) -> str:
        kind = "thumbnail" if self.thumbnail_key else "file"
        return f"/api/v1/media/{self.id}/{kind}?v={self.sha256[:12]}"


class Usage(BaseModel):
    link_id: int
    entity_type: str
    entity_id: int
    entity_name: str | None
    is_primary: bool


class MediaDetail(MediaOut):
    usages: list[Usage] = []


class UploadResult(BaseModel):
    media: MediaOut
    created: bool  # False = identical image already existed and was reused
    link_id: int | None = None


class MediaUpdate(BaseModel):
    description: OptStr = Field(default=None, max_length=1000)
    alt_text: OptStr = Field(default=None, max_length=300)
    source: Source | None = None
    is_illustrative: bool | None = None


class GalleryItem(ORMModel):
    id: int  # link id
    media_id: int
    is_primary: bool
    sort_order: int
    caption: str | None
    media: MediaOut


class LinkCreate(BaseModel):
    entity_type: EntityType
    entity_id: int
    media_id: int
    caption: OptStr = Field(default=None, max_length=300)


class ReorderBody(BaseModel):
    link_ids: list[int]


class CaptionBody(BaseModel):
    caption: OptStr = Field(default=None, max_length=300)
