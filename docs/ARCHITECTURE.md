# Architecture

Modular monolith: one FastAPI backend and one Next.js frontend, talking REST/JSON. No microservices.

```
Browser (this laptop or another machine on the LAN)
   │  http://<host>:3000            pages + /api/v1/* (same origin)
   ▼
Next.js (port 3000) ──rewrite /api/v1/*──► FastAPI (127.0.0.1:8000/api/v1, never exposed)
                                                  │
                     api/ (routers: HTTP only, no business logic)
                                                  │
                     services/ (use cases, validation, orchestration)
                       │                 │                  │
               engines/ (pure,     repositories/       services/storage.py
               deterministic:      (SQLAlchemy          (FileStorage interface:
               itinerary, route,    queries)              Local now, Blob/S3 later)
               pricing)                 │
                                    models/ ──► SQLite (PostgreSQL later)
```

## Backend layers (`backend/app`)

| Folder | Responsibility | Rule |
|---|---|---|
| `api/v1/` | FastAPI routers, request/response models, dependencies | No SQL, no business rules |
| `schemas/` | Pydantic DTOs. Customer-facing and internal DTOs are **separate classes** | Internal cost fields never appear in customer DTOs |
| `services/` | Use cases: CRM, inventory, media, itinerary, pdf, pricing | Transaction boundaries live here |
| `engines/` | Pure functions: itinerary generation, route sequencing, pricing math | No DB or HTTP access; fully unit-testable |
| `repositories/` | Data access | The only place that builds queries |
| `models/` | SQLAlchemy ORM models | Registered in `models/__init__.py` for Alembic |
| `core/` | Config (`YANA_*` env vars), error handling | |
| `database/` | Engine, session, declarative base, mixins | SQLite PRAGMAs applied only for SQLite |

Abstractions designed for cloud migration (PRD 24):
- **Storage**: `FileStorage` (save/read/delete/exists on relative keys). `LocalFileStorage` blocks path traversal.
- **PDF renderer** (Phase 6): `PdfRenderer` interface, `PlaywrightPdfRenderer` implementation.
- **AI provider** (Phase 8): `AIProvider` / `ImageGenerationProvider` interfaces with a `NullProvider` default, so the app runs without AI.

Errors: every failure returns `{error, message, details?}` JSON (`core/errors.py`). Services raise `DomainError`.

## Frontend (`frontend/`)

| Folder | Purpose |
|---|---|
| `app/` | Routes (App Router). Pages stay thin and compose features |
| `components/ui/` | shadcn/ui primitives (Base UI) |
| `components/layout/` | App shell, sidebar |
| `features/<module>/` | Module-specific components and logic (dashboard, crm, inventory, itinerary…) |
| `services/` | API client (`apiFetch`, typed per-module clients) |
| `hooks/`, `types/` | Shared hooks and API types |
| `tests/` | Vitest unit tests |

Navigation lives in `features/navigation/nav-config.ts`. A module is shown only when `enabled: true` (PRD 5.2: hide unimplemented modules).

No itinerary, pricing or route logic runs in the frontend.

## Configuration

Backend: `.env` at project root (see `.env.example`). Relative paths resolve against the project root. Frontend: `frontend/.env.local` → `BACKEND_URL` (server-side; where `/api/v1` is forwarded, default `http://127.0.0.1:8000`).

## Data locations

| Data | Location | In git? |
|---|---|---|
| SQLite DB | `database/yana_studio.db` | No |
| Uploaded images | `uploads/<category>/<uuid>.<ext>` (DB stores relative key) | No |
| Generated PDFs | `exports/itineraries/` | No |
| Backups | `database/backups/` | No |
