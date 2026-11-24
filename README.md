# YANA Travel Studio

Local-first B2B travel management and itinerary-proposal platform for **YANA DMC**. It turns travel-agent requirements into customised European itineraries and branded PDF proposals.

> **Status:** Phase 1 (UI foundation & CRM) complete. See [docs/DEVELOPMENT_PROGRESS.md](docs/DEVELOPMENT_PROGRESS.md).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui · Lucide |
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic 2 · Alembic |
| Database | SQLite (local) → PostgreSQL-ready |
| Storage | Local filesystem behind a storage abstraction |
| PDF (Phase 6) | One HTML/CSS template (Classic / Premium / Explorer), printed by Playwright with the installed Microsoft Edge (or Chrome); offline SVG route maps |

## Prerequisites (Windows)

- Python 3.11 (`py -3.11 --version`)
- Node.js 20+ (tested with 24) and npm
- Git

## First-time setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

This creates `backend\.venv`, installs dependencies, creates `.env` with a random `YANA_SECRET_KEY`, runs database migrations, **asks you to create the first administrator** (email, name, password), installs frontend packages and creates `frontend\.env.local`. It's safe to re-run.

Optional: load demonstration inventory (8 countries, real attractions, fictional DEMO hotels and restaurants) into an empty inventory with `cd backend; .\.venv\Scripts\python.exe -m app.cli seed-demo`.

Back up with `scripts\backup.ps1` (or *Administration → Backups & data*); restore with `scripts\restore.ps1 -File <zip>` while the app is stopped.

Add another administrator later with `scripts\create-admin.ps1`; other users are managed in the app under **Administration → Users**.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1      # opens backend + frontend windows
```

Or separately: `scripts\start-backend.ps1` and `scripts\start-frontend.ps1`.

| What | URL |
|---|---|
| App | http://localhost:3000 |
| API docs (Swagger, this laptop only) | http://localhost:8000/docs |
| Health check | http://localhost:3000/api/v1/health |

## Share with other computers on your network

`start.ps1` is for working on this laptop only. To let colleagues on the **same network** (office LAN or Wi‑Fi) use the app:

1. **Once, as Administrator**, allow the port through Windows Firewall:
   right-click PowerShell → *Run as administrator* →
   `powershell -ExecutionPolicy Bypass -File scripts\allow-firewall.ps1`
2. Make sure Windows treats the network as **Private** (or Domain): *Settings → Network & internet → Wi‑Fi/Ethernet → your network → Network profile type: Private*. Windows blocks incoming connections on **Public** networks.
3. Start in shared mode:
   `powershell -ExecutionPolicy Bypass -File scripts\start-shared.ps1`
   It prints the address to give colleagues, e.g. `http://192.168.1.25:3000`.

How it works: other machines only talk to port 3000. The Next.js server forwards `/api/v1/*` to the backend, which stays private on `127.0.0.1:8000`.

> **Security:** traffic is plain HTTP, so passwords and data cross the network unencrypted. Use shared mode only on trusted networks, give every person their own account, and use strong passwords. Internet access (outside your network) needs a proper HTTPS deployment; see `docs/DEVELOPMENT_PLAN.md`. On a company-managed laptop, IT policy may block incoming connections regardless of these settings.

### Private remote access (requires IT approval on company devices)

`scripts\start-tailscale.ps1` serves the app privately to your own Tailscale devices (e.g. your phone) over HTTPS, without opening ports. **Do not use it on a company laptop without IT approval.** Turn it off with `tailscale serve reset` and `tailscale down`.

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
