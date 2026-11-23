"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.services.storage import get_storage


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    get_storage().ensure_layout()
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    (settings.exports_dir / "itineraries").mkdir(exist_ok=True)
    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description="Backend API for YANA Travel Studio (YANA DMC).",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
