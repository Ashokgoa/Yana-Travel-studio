# YANA Travel Studio

Local-first B2B travel management and itinerary-proposal platform for **YANA DMC**. It turns travel-agent requirements into customised European itineraries and branded PDF proposals.

> **Status:** Phase 0 (foundation) complete. See [docs/DEVELOPMENT_PROGRESS.md](docs/DEVELOPMENT_PROGRESS.md).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui · Lucide |
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic 2 · Alembic |
| Database | SQLite (local) → PostgreSQL-ready |
| Storage | Local filesystem behind a storage abstraction |
| PDF (Phase 6) | HTML/CSS templates rendered by Playwright (Chromium / Edge) |

## Prerequisites (Windows)

- Python 3.11 (`py -3.11 --version`)
- Node.js 20+ (tested with 24) and npm
- Git

## First-time setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

This creates `backend\.venv`, installs dependencies, runs database migrations, installs frontend packages, and copies `.env.example` → `.env` / `frontend\.env.local`.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1      # opens backend + frontend windows
```

Or separately: `scripts\start-backend.ps1` and `scripts\start-frontend.ps1`.

| What | URL |
|---|---|
| App | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |

## Test

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

Runs backend pytest, frontend typecheck, ESLint and Vitest.

## Database migrations

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head                        # apply
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "msg"    # after changing models
```

## Project layout

```
backend/        FastAPI app (api → services → repositories → models; engines for business logic)
frontend/       Next.js app
database/       Alembic migrations, seed data, local SQLite file (git-ignored)
uploads/        Uploaded images by category (git-ignored)
pdf_templates/  Classic / Premium / Explorer brochure templates
exports/        Generated PDFs (git-ignored)
docs/           PRD, architecture, database design, API docs, progress, decisions
scripts/        Setup / start / test scripts
```

## Documentation

- [Development plan, risks & open decisions](docs/DEVELOPMENT_PLAN.md)
- [PRD summary](docs/PRD.md) · [Architecture](docs/ARCHITECTURE.md) · [Database design](docs/DATABASE_DESIGN.md)
- [API documentation](docs/API_DOCUMENTATION.md) · [Technical decisions](docs/TECHNICAL_DECISIONS.md) · [User guide](docs/USER_GUIDE.md)

## Data protection

Customer data, the database file, uploaded images, generated PDFs and `.env` files are git-ignored and must never be committed.
