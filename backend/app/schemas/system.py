from typing import Literal

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    status: Literal["ok", "error"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_name: str
    version: str
    environment: str
    database: ComponentStatus
    storage: ComponentStatus
    exports: ComponentStatus


class ErrorResponse(BaseModel):
    """Uniform error body returned by every failing endpoint."""

    error: str
    message: str
    details: list[dict] | None = None
