"""HTML rendering of proposals (shared by the live preview and the PDF) and the
PDF renderer abstraction (ARCHITECTURE: `PdfRenderer` / `PlaywrightPdfRenderer`)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from fastapi import status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from app.core.config import get_settings
from app.core.errors import DomainError
from app.services.proposal_content import ProposalDocument

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "proposal"
log = logging.getLogger("yana.pdf")


def _css_string(value: str) -> Markup:
    """Quote text for a CSS `content:` value inside <style> (no HTML entities there)."""
    safe = "".join(ch if ch.isalnum() or ch in " .,·&'-()" else f"\{ord(ch):x} " for ch in value or "")
    return Markup(f'"{safe}"')


@lru_cache(maxsize=1)
def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["css_string"] = _css_string
    return env


def render_html(doc: ProposalDocument) -> str:
    return _env().get_template("proposal.html.j2").render(doc=doc, d=asdict)


class PdfRenderer(ABC):
    @abstractmethod
    def render(self, html: str) -> bytes: ...


class PlaywrightPdfRenderer(PdfRenderer):
    """Prints HTML to an A4 PDF with headless Edge or Chrome (installed browser, no download needed).

    The page has no network access: every image, flag and map is embedded in the HTML.
    """

    def __init__(self, channel: str | None = None):
        self.channel = channel if channel is not None else get_settings().pdf_browser_channel

    def render(self, html: str) -> bytes:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise DomainError("PDF export is not available: the 'playwright' package is not installed.",
                              status.HTTP_503_SERVICE_UNAVAILABLE, "pdf_unavailable") from exc
        channels = [self.channel] if self.channel else []
        channels += [c for c in ("msedge", "chrome", "") if c not in channels]
        last_error: Exception | None = None
        with sync_playwright() as p:
            for channel in channels:
                try:
                    browser = p.chromium.launch(channel=channel or None)
                except PlaywrightError as exc:
                    last_error = exc
                    continue
                try:
                    context = browser.new_context(java_script_enabled=False, offline=True)
                    page = context.new_page()
                    page.set_content(html, wait_until="load")
                    return page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
                finally:
                    browser.close()
        log.error("No browser available for PDF export: %s", last_error)
        raise DomainError("PDF export needs Microsoft Edge or Google Chrome installed on the server.",
                          status.HTTP_503_SERVICE_UNAVAILABLE, "pdf_unavailable")


def get_pdf_renderer() -> PdfRenderer:
    return PlaywrightPdfRenderer()
