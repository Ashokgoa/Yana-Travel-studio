# Development Progress

| Phase | Name | Status |
|---|---|---|
| 0 | Project foundation | ✅ Complete (2026-11-23) |
| 1 | UI foundation & CRM | ✅ Complete (2026-11-23), awaiting approval |
| 2 | Destination inventory & images | ✅ Complete (2026-11-24) |
| 3 | Customer requirement capture | ✅ Complete (2026-11-24) |
| 4 | Itinerary engine | ✅ Complete (2026-11-24) |
| 5 | Visual itinerary builder | ✅ Complete (2026-11-24), awaiting approval |
| 6 | PDF designer | ⏳ Next |
| 7 | Pricing & costing | Planned |
| 8 | AI integration | Planned |

---

## Phase 5 – Visual itinerary builder (2026-11-24)

### Done: backend (5a)
- **Versioning**: generated versions are read-only snapshots (migration `0006` locks existing ones). *Start editing* clones the latest saved version into a working copy; *Save version* (label + notes) locks it; *Restore* copies any earlier version into a new working copy (an open draft is auto-saved first, so nothing is lost); *Compare* lists the differences in plain English (days, nights per city, hotels, sightseeing, vehicle, estimated cost); *Duplicate* copies an itinerary.
- **Edits on the working copy** (409 `version_locked` otherwise):
  - add, duplicate or remove days (arrival and departure days protected);
  - edit day text;
  - add sightseeing from inventory or free-time/custom activities;
  - edit, move (any day, position or slot) or remove activities;
  - set meals (hotel, restaurant from inventory, own, none);
  - replace a hotel (same city only; rooms re-mapped and re-priced; the previous hotel is kept as an alternative);
  - change the vehicle or a leg's mode (e.g. train).
- **Consistency**: after day changes, hotel stays and inter-city legs are rebuilt from the days. Previous hotel choices and transport are kept where they still apply, and days, nights, dates and route always add up.
- **Live checks and cost estimate**, recomputed on every view: duplicate sightseeing, wrong city, closed weekday, child-unsuitable, overloaded days, unverified dietary choices, meals to arrange, missing or inactive or below-category hotels, vehicle seats and operating countries, long legs, unpriced items, over budget.
- Tests: 8 new builder tests covering PRD Part 25 cases 11–14 and 16–17 (130 backend tests in total).

### Done: editor screens (5b)
- **Itinerary builder** (`/itineraries/{id}/edit`, opened via *Edit itinerary*):
  - Read-only banner for saved versions, with *Start editing*.
  - Per day: rename, add a day after, duplicate, remove (confirmed).
  - Activities: drag handle, ↑/↓ (which also moves to the previous or next day), time-of-day, edit, remove.
  - *Add sightseeing or free time*: inventory picker for the day's city that marks "already on day N", plus free-time and custom activities.
  - Meals per day: hotel, any restaurant in the city (✓ diet verified / ⚠ not verified), own arrangement, not included.
- **Side panels**: estimated cost, live checks, hotels with *Replace* (city hotels with stars, price from, DEMO), vehicle choice, road/train per leg.
- **Versions dialog**: list, view any version read-only (`?version=N` on the day-by-day page), restore, compare any two in plain English. *Save version* with name and notes; *Duplicate* itinerary.
- **Bugs found by the browser test and fixed**: three dropdowns (leg mode, vehicle, time of day) read the selected value only after React had restored the old value, so the change was lost. The value is now read immediately. "By road" now returns a leg to the trip's own road vehicle type.
- Real browser, **development mode**: start editing, add day, add sightseeing, arrow move, meal, replace hotel, time of day, train leg (each verified on the server), save version, compare, restore. 19 checks pass with zero console warnings.

### Known limits
- Drag and drop is verified manually (headless browsers can't reliably simulate it); the ↑/↓ buttons use the same backend operation and are covered by automated tests.
- Changing a day's *city* is done by removing or adding days around stays (cities come from the route); a "move to another city" action can follow if needed.

---

## Phase 4 – Itinerary engine (2026-11-24)

### Delivered
- **Deterministic engine** (`backend/app/engines/itinerary_engine.py`, pure functions, no AI):
  1. Validates requirements, refusing with a clear list if incomplete.
  2. Chooses cities: must-visits are never dropped; preferred and optional are ranked by strategy; avoided places are excluded; arrival and departure cities come from the airports; cities with hotels are preferred.
  3. Orders the route with nearest-neighbour plus 2-opt, with fixed start and end.
  4. Allocates nights to match the trip exactly, using pace, minimum nights, unseen sightseeing and strategy affinity.
  5. Plans days by interests, children's suitability and opening days.
  6. Plans meals only at restaurants with *verified* dietary options (Indian first for Indian preferences).
  7. Matches hotels by stars, style, location, breakfast and room fit, with alternatives.
  8. Picks the vehicle by seats and operating countries, with train for long legs if requested.
  9. Estimates costs and compares them with the budget.
- **Three strategies**: Classic, Scenic and Premium, each with *explanations* (why) and *warnings* (what to check). If must-visits cannot fit, it explains instead of dropping them.
- **Geography** (`engines/geo.py`): great-circle × 1.25 road factor, 70 km/h coach average plus EU driver breaks. Always labelled *estimate*.
- **Storage** (migration `0005`): itineraries → versions → days → activities and meals, plus stays and transports. All rows reference inventory records; the engine report is kept on the version.
- **API**: generate, list per enquiry, saved itineraries, and full day-by-day detail with resolved names and images.
- **Screens**: *Itineraries* section on the enquiry page (generate or regenerate), side-by-side **Compare** with lowest values highlighted, **day-by-day page** (offline route map, points to check, why this plan, hotels, cost estimate), and **Saved Itineraries**.

### Verification
- 18 engine tests on the demo geography covering PRD Part 25 cases 1–10 and 15 (7, 12 and 15 days; 2 and 6 countries; mandatory; children; Jain; 5★; limited budget; three alternatives), plus avoid rules, costs, vehicles, and day/night/date consistency.
- 5 API tests (incomplete requirements, end-to-end generation, regeneration batches, inactive hotels never proposed, explained impossibility). 122 backend tests in total.
- Quality review of the generated plans led to engine improvements: prefer cities with hotels; arrival/departure cities don't "cover" a must-visit country; spare nights go where sightseeing remains; strategy affinity; child-unsuitable attractions excluded; Indian restaurants first for Indian preferences.
- Real browser (development mode): generate → compare → day-by-day → saved list, all checks pass with zero console warnings.

### Outstanding / known limits
- Distances and times are straight-line estimates (no routing service); planners should verify long legs.
- Many demo attractions have no ticket price, so those costs show as "no price" (not invented).
- Map labels for very close cities can touch; the PDF map (Phase 6) will be refined.
- Editing itineraries (move activities, replace hotels, versions) is Phase 5.

---

## Phase 3 – Customer requirement capture (2026-11-24)

### Delivered
- Migration `0004`: `enquiry_requirements` (one per enquiry) and `enquiry_destinations` (country, optional city, preference must-visit/preferred/optional/avoid, minimum nights, order).
- 9-step wizard (`/crm/enquiries/{id}/requirements`): Travellers, Travel, Destinations, Interests, Hotels, Food, Transport, Budget, Notes, plus a Review step. Saves on every step (drafts allowed), unsaved-changes warning, step progress, and a readiness panel.
- Pre-filled from the enquiry and customer (travellers, children's ages, dates, budget). Saving keeps the enquiry summary in sync and moves a *New* enquiry to *In Progress* (recorded in its history). New enquiries open the wizard straight away.
- Validation (PRD 13.2 step 1): **missing** items (dates, airports, destinations, budget) and **warnings** (more must-visit places than nights, minimum nights exceed the trip, start/end country marked avoid, rooms or vehicle too small, budget per person vs total mismatch, Jain verified-only notice). Nothing is silently dropped.
- Enquiry page shows the full requirements summary and readiness.

### Verification
- 11 new backend tests incl. the PRD Part 28 scenario (99 total, 3 consecutive runs, no skips).
- Real browser, **development mode** (catches React warnings): full wizard run with dates, 7 destinations incl. a city and an avoided country, rooms, food, transport, budget, notes, review and finish. All checks pass with zero console warnings or errors.
- Found and fixed during testing: the review step falsely showed "unsaved changes" after saving (server-normalised values); a duplicate React key in hotel dialogs; random country codes occasionally skipping tests.

### Outstanding
- Cities dropdown loads up to 100 cities; a searchable picker will be needed for a much larger inventory.

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
