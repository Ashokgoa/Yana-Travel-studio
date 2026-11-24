# YANA Travel Studio – guidance for Claude Code

Read `docs/PRD.md` (rules), `docs/DEVELOPMENT_PLAN.md` (risks, open decisions) and `docs/DEVELOPMENT_PROGRESS.md` (current phase) before starting work.

## Working rules
- Work **one phase at a time**. After each milestone: run `scripts\test.ps1`, update `docs/DEVELOPMENT_PROGRESS.md` (plus API, database and decision docs as relevant), summarise, and **wait for approval** before the next phase.
- Backend layering: `api` (HTTP only) → `services` → `repositories` / `engines` (pure logic) → `models`. No business logic in routers or React components.
- Every model change needs an Alembic migration (`python -m alembic revision --autogenerate`). Review the generated file.
- Customer-facing DTOs and PDFs must never include costs, margins or supplier prices. Use separate schema classes.
- Never invent prices, availability or dietary support. Unknown means NULL or unknown. Prices default to unverified ("Estimated").
- Frontend is Next.js 16: check `frontend/node_modules/next/dist/docs/` before using Next APIs. shadcn/ui uses Base UI (`render` prop, not `asChild`).
- Add a nav item by setting `enabled: true` in `frontend/features/navigation/nav-config.ts` only when the module works.
- Never commit `.env`, the database, uploads, exports or customer data.

## Commands
- Backend tests: `cd backend; .\.venv\Scripts\python.exe -m pytest`
- Frontend: `cd frontend; npm run typecheck; npm run lint; npm test`
- Run: `scripts\start.ps1`
- Backup / restore: `scripts\backup.ps1`, `scripts\restore.ps1 -File <zip>` (app stopped)
- Optional Claude provider: `pip install -r backend/requirements-ai.txt` + `YANA_AI_PROVIDER=claude` (only with IT approval)
