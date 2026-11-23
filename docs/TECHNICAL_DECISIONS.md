# Technical Decisions

Lightweight decision records. Newest at the bottom.

### TD-001 · Modular monolith, REST, separate frontend/backend (Phase 0)
PRD Parts 4 and 24. Keeps deployment simple locally and lets either side move to the cloud independently.

### TD-002 · Alembic migrations live in `database/migrations`, config in `backend/alembic.ini`
Matches the PRD folder layout. `env.py` reads the URL from application settings, so there's one source of truth. `render_as_batch=True` makes ALTERs work on SQLite.

### TD-003 · Reference roles seeded in the migration
`admin` and `planner` are inserted by migration `0001`, so a fresh DB is always usable. Demo inventory will be a separate, optional seed script, because it isn't reference data.

### TD-004 · Environment config with `YANA_` prefix (pydantic-settings)
No hardcoded absolute paths. Relative storage paths resolve against the project root, so the app works wherever the folder is cloned.

### TD-005 · Storage abstraction with relative keys
The DB stores `hotels/<uuid>.jpg`, never absolute paths. Uploaded filenames are replaced by UUIDs (safe names, no collisions). Path traversal is rejected in `LocalFileStorage._resolve`.

### TD-006 · Uniform JSON error envelope
`{error, message, details?}` for all errors, including validation errors, which return a field-level `details` list for form display. Unhandled exceptions are logged and return a generic 500 message.

### TD-007 · Frontend: Next.js 16, Tailwind 4, shadcn/ui (base-nova style on Base UI)
These are the current versions from `create-next-app` / `shadcn init`. shadcn now uses `@base-ui/react` and the `cn` package (from the shadcn-ui org) instead of Radix and `clsx`/`tailwind-merge`. Buttons use Base UI's `render` prop rather than `asChild`.

### TD-008 · Placeholder brand palette as CSS tokens
YANA DMC's official colours couldn't be determined from the public website. A navy / teal / gold palette is defined once in `frontend/app/globals.css` (`--brand-*`) and will be replaced when YANA supplies brand values. The sidebar shows a text wordmark, never a recreated logo.

### TD-009 · Unimplemented modules hidden
`nav-config.ts` holds the full PRD navigation with `enabled` flags, covered by a unit test.

### TD-010 · Vitest for frontend unit tests
Vitest 3 pulled in `tinypool` with a critical advisory, so we use Vitest 5. `@types/node` was aligned to Node 24 (the installed runtime).

### TD-011 · Route distances are estimates (planned, Phase 4)
Great-circle distance × road factor plus average speed, flagged `is_estimate=true` and shown as "Estimated". No paid routing API. See DEVELOPMENT_PLAN risk R3.

### TD-012 · PDF route maps as offline SVG (planned, Phase 6)
This avoids live tile fetching in headless Chromium and keeps us within OSM tile usage policy. Leaflet is used for the interactive UI only.
