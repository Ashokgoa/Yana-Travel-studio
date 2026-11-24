"""PDF proposal settings and exports (Phase 6).

Customer-facing output never includes supplier costs or margins: the only price
a proposal can show is the selling price the planner types in (`price_per_person`).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TEMPLATES = ("classic", "premium", "explorer")
BRANDING = ("agent", "yana", "both")
SECTION_KEYS = ("cover", "highlights", "route_map", "days", "hotels", "summary", "price", "inclusions", "terms", "closing")
SECTION_LABELS = {
    "cover": "Cover and introduction",
    "highlights": "Tour highlights",
    "route_map": "Route map",
    "days": "Day-by-day programme",
    "hotels": "Hotels",
    "summary": "Country and day summary",
    "price": "Price",
    "inclusions": "Inclusions and exclusions",
    "terms": "Terms and conditions",
    "closing": "Closing message",
}
HEX = r"^#[0-9A-Fa-f]{6}$"


class SectionSetting(BaseModel):
    key: Literal[SECTION_KEYS]  # type: ignore[valid-type]
    enabled: bool = True


def default_sections() -> list[SectionSetting]:
    return [SectionSetting(key=k) for k in SECTION_KEYS]


class ProposalSettings(BaseModel):
    """Per-itinerary designer settings. `None` text fields mean 'use the automatic text'."""

    template: Literal[TEMPLATES] = "classic"  # type: ignore[valid-type]
    branding: Literal[BRANDING] = "agent"  # type: ignore[valid-type]
    sections: list[SectionSetting] = Field(default_factory=default_sections)
    title: str | None = Field(default=None, max_length=120)
    intro: str | None = Field(default=None, max_length=2000)
    closing: str | None = Field(default=None, max_length=1000)
    inclusions: list[str] | None = Field(default=None, max_length=40)
    exclusions: list[str] | None = Field(default=None, max_length=40)
    terms: str | None = Field(default=None, max_length=8000)
    hotel_names_in_days: bool = True
    price_per_person: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    price_currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")
    price_note: str | None = Field(default=None, max_length=300)
    # Day number (as text) -> media id; 0 hides the photo for that day.
    day_images: dict[str, int] = Field(default_factory=dict)
    primary_color: str | None = Field(default=None, pattern=HEX)
    accent_color: str | None = Field(default=None, pattern=HEX)

    @field_validator("sections")
    @classmethod
    def _complete_sections(cls, value: list[SectionSetting]) -> list[SectionSetting]:
        """Keep the given order, drop duplicates and append any section that is missing."""
        seen, out = set(), []
        for s in value:
            if s.key not in seen:
                seen.add(s.key)
                out.append(s)
        out.extend(SectionSetting(key=k) for k in SECTION_KEYS if k not in seen)
        return out

    @field_validator("inclusions", "exclusions")
    @classmethod
    def _clean_lines(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [line.strip()[:300] for line in value if line and line.strip()]


class BrandingSettings(BaseModel):
    """YANA branding and proposal defaults (administrators)."""

    company_name: str = Field(default="YANA DMC", max_length=120)
    tagline: str | None = Field(default=None, max_length=200)
    contact_line: str | None = Field(default=None, max_length=300)
    logo_media_id: int | None = None
    primary_color: str = Field(default="#1F3B64", pattern=HEX)
    accent_color: str = Field(default="#E0A100", pattern=HEX)
    default_closing: str = Field(
        default="Every journey has its ending, but the memories stay with us. Thank you for travelling with us; we hope to welcome you on another adventure soon!",
        max_length=1000,
    )
    default_exclusions: list[str] = Field(default_factory=lambda: [
        "International flights and airport taxes",
        "Visa fees and travel insurance",
        "Meals, drinks and services not mentioned in the itinerary",
        "Personal expenses, tips and porterage",
        "City taxes payable locally at hotels, where applicable",
    ])
    default_terms: str = Field(
        default=(
            "This proposal is for planning purposes and is subject to availability at the time of booking.\n"
            "Prices, hotels and sightseeing are confirmed only after booking; timings may change because of local conditions.\n"
            "Payment, cancellation and amendment conditions will be shared with the booking confirmation."
        ),
        max_length=8000,
    )
    terms_reviewed: bool = False  # admins confirm the default terms have been replaced with YANA's own


class ProposalExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    itinerary_id: int
    version_number: int
    filename: str
    template: str
    branding: str
    size_bytes: int
    created_at: datetime
    created_by_name: str | None = None


class ProposalOptions(BaseModel):
    templates: list[dict]
    sections: list[dict]
    day_images: list[dict]  # [{day_number, title, choices: [{media_id, url, label}]}]
    internal_estimate_per_person: str | None  # INTERNAL hint for the planner; never rendered in the PDF
    currency: str
