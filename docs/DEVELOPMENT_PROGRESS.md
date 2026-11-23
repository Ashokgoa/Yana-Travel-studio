# Development Progress

| Phase | Name | Status |
|---|---|---|
| 0 | Project foundation | ✅ Complete (2026-11-23) |
| 1 | UI foundation & CRM | ✅ Complete (2026-11-23), awaiting approval |
| 2 | Destination inventory & images | ✅ Complete (2026-11-24), awaiting approval |
| 3 | Customer requirement capture | ⏳ Next |
| 4 | Itinerary engine | Planned |
| 5 | Visual itinerary builder | Planned |
| 6 | PDF designer | Planned |
| 7 | Pricing & costing | Planned |
| 8 | AI integration | Planned |

---

## Phase 2 – Destination inventory & images (2026-11-23 → 24)

### 2a · Inventory data model & API (done)
- Migration `0003`: countries, cities, suppliers, attractions, hotels with room types and seasonal rates, restaurants, vehicle categories (7 PRD categories seeded) and vehicles with operating countries, media and media links.
- One declarative CRUD engine for every inventory type: search, filters, pagination, reference checks, duplicate detection, activate/deactivate. Planners read; admins write.
- Business rules: prices unverified by default ("estimated"); restaurant dietary flags are NULL = unknown and filters only return verified Yes; vocabularies validated.

### 2b · Inventory screens (done)
- Config-driven list, detail and form for Countries, Cities, Sightseeing, Hotels, Restaurants, Transportation and Suppliers (`features/inventory/resource-config.tsx`). Adding a field is a config change.
- Hotels: room types and seasonal rates with add/edit/delete.
- Yes/No/Unknown inputs for facts that must be verified; DEMO badges and banner; estimated/verified price labels; OpenStreetMap links for coordinates.
- Verified in headless Edge: an admin created a hotel through the UI (validation messages, save, detail page, room type with estimated price), with zero page errors.

### 2d · Demo inventory (done, pulled forward for testing)
- `python -m app.cli seed-demo` loads 8 countries, 26 cities, 30 real attractions and fictional DEMO hotels (16), restaurants (10), suppliers (4) and vehicles (5). It refuses to run if any country exists, so it never overwrites real data.
- No invented opening hours or ticket prices for real attractions; all demo prices are unverified (test enforced).

### 2c · Image library (done)
- Upload JPG/PNG/WEBP (≤10 MB): real format detected from content, decompression-bomb limit, EXIF orientation applied, **all metadata incl. GPS removed**, long edge capped at 2400 px, 480 px JPEG thumbnail. Identical files are stored once (SHA-256) and re-linked.
- Galleries on every inventory record: upload (multi-file, drag and drop), add from library (reuse), primary image (first upload automatic; promoted when removed), reorder (arrows + drag and drop), captions, remove from record, replace file everywhere, delete everywhere. AI images are always flagged illustrative.
- Central **Image Library** page: search, category and photo/illustrative filters, usage ("used in N places") with links.
- Permissions: anyone signed in views and uploads to the library; gallery changes, metadata edits, replace and delete are admin-only.
- Verified: 16 new backend tests (88 total). Real browser upload through the Next.js proxy; primary/reorder/list thumbnail/library/details checks all pass; stored files confirmed to have no metadata.

### Outstanding / known issues
- Images are served through the API with authentication (fine locally). For cloud hosting they should move to Blob storage with signed URLs.
- Reference dropdowns load up to 100 records (fine for current inventory size).
- Demo data loaded into the local database on request; replace or deactivate it before real proposals.

---

## Phase 1 – UI foundation & CRM (2026-11-23)

### Decisions applied
- **Real login** (decided by YANA): email + password, Argon2 hashes, signed session token in an HttpOnly cookie, roles enforced by the backend.
- **Enquiry reference format** (decided by YANA): `ENQ-2026-0001` (prefix, year, running number that restarts each year).

### Delivered
- **Auth & roles**: `/auth/login|logout|me`; Administrator / Travel Planner; admin-only user management (`/users`), with protections against removing the last admin or deactivating yourself. `scripts\setup.ps1` generates `YANA_SECRET_KEY` and prompts for the first admin; `scripts\create-admin.ps1` adds more.
- **Travel agents**: create, edit, view, search (name/contact/email/phone), filter by status and country, deactivate/reactivate, customer and enquiry counts.
- **Customers**: create, edit, view, search, filter by agent and status; traveller counts with per-child ages (validated); linked to an agent or "direct".
- **Enquiries**: auto-numbered references, all 8 PRD statuses, status changes recorded with who/when/note, assigned planner, budget (amount, currency, per person/group), travel dates with day/night count, internal comments. Search plus filters by status, agent, planner and date range. Guards against mismatched agent/customer and inactive agents.
- **Dashboard**: PRD Part 20 metrics (total, new, in progress, proposals generated, awaiting response, approved, confirmed), recent enquiries, quick actions, system status (admins).
- **UI**: login page, role-aware sidebar with user menu and sign-out, reusable components (page header, form field, native select, search, pagination, empty/error/loading states, status badges, form dialog, confirm dialog), field-level server validation messages, toasts.

### Verification
- Backend: **49 pytest tests pass** (auth, permissions, user admin, CRM CRUD/search/filter/pagination, validation, reference sequence, status history, dashboard counts, migrations).
- Frontend: typecheck, ESLint, **5 Vitest tests**, production build all pass.
- End-to-end against a throwaway database: an API script exercised the full workflow, and headless Edge logged in through the real login form and rendered every screen with **zero console errors**. This visual check found and fixed: preselected dropdown values lost while options load, a clipped dashboard table, and badge fonts inside headings.

### Outstanding / known issues
- Agent/customer dropdowns load up to 100 active records; a searchable picker will be needed as the agent list grows.
- `npm audit`: still the same 4 moderate advisories as Phase 0 (shadcn CLI dev tooling → `minimatch`), none in app runtime code.
- Starlette `httpx2` deprecation warning (unchanged from Phase 0).
- Brand colours, fonts and logo are still placeholders.

---

## Phase 0 – Project foundation (2026-11-23)

### Delivered
- Project structure per PRD 4.2 (`backend/`, `frontend/`, `database/`, `uploads/`, `pdf_templates/`, `exports/`, `docs/`, `scripts/`).
- **Backend**: FastAPI app factory, env-based settings, layered folders, SQLite with foreign keys and WAL, SQLAlchemy 2 base with timestamp mixins and naming conventions, uniform error handling, CORS for the frontend, `FileStorage` abstraction with path-traversal protection, `GET /api/v1/health`, OpenAPI docs at `/docs`.
- **Database**: Alembic configured; migration `0001` creates `roles` (seeded admin/planner), `users`, `app_settings`.
- **Frontend**: Next.js 16 + TypeScript + Tailwind 4 + shadcn/ui + Lucide. Responsive app shell (fixed sidebar on desktop, slide-over on tablet), placeholder brand theme, dashboard with live system status and phase roadmap, typed API client, navigation config that hides unimplemented modules.
- **Scripts**: `setup.ps1`, `start.ps1`, `start-backend.ps1`, `start-frontend.ps1`, `test.ps1`.
- **Docs**: README, PRD summary, development plan (dependencies, risks, schema, milestones, open decisions), architecture, database design, API docs, technical decisions, user guide stub.

### Verification
- Backend: 19 pytest tests pass (health, startup storage layout, OpenAPI, JSON 404, CORS, seeded roles, FK enforcement, timestamps, migration up/down round-trip, storage traversal, config).
- Frontend: `tsc --noEmit` clean, ESLint clean, Vitest 3/3 pass, `next build` succeeds.
- Manual: both servers started; dashboard shows "Operational" with DB at migration 0001.

### Outstanding / known issues
- Starlette warns that its TestClient prefers `httpx2` over `httpx`. Harmless; the switch was not made in this session.
- `npm audit`: 4 moderate advisories in the shadcn CLI's dev tooling (`ts-morph` → `minimatch`), not in app runtime code. The only fix is a breaking downgrade, so it was not applied.
- Brand colours, fonts and logo are placeholders until YANA DMC provides them.
- Authentication approach is undecided (see DEVELOPMENT_PLAN §6, item 14).
