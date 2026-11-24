"""PDF proposal exports (Phase 6). Each export is linked to the exact itinerary
version it was made from, with the designer settings used, so it can be traced
and downloaded again later."""

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin
from app.models.user import User


class ProposalExport(IdMixin, TimestampMixin, Base):
    __tablename__ = "proposal_exports"

    itinerary_id: Mapped[int] = mapped_column(ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("itinerary_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)  # relative to exports_dir
    filename: Mapped[str] = mapped_column(String(200), nullable=False)  # download name: YANA_<Tour>_<Customer>_V<n>.pdf
    template: Mapped[str] = mapped_column(String(20), nullable=False)
    branding: Mapped[str] = mapped_column(String(10), nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_by: Mapped[User | None] = relationship()
