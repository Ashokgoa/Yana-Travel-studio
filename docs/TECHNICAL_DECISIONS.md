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

### TD-013 · Authentication: Argon2 + signed token in an HttpOnly cookie (Phase 1)
YANA chose real login. Passwords are hashed with Argon2 (`pwdlib`). Login returns a JWT (HS256, `YANA_SECRET_KEY`, 12 h default) in an **HttpOnly, SameSite=Lax** cookie, so JavaScript can't read it. The backend also accepts `Authorization: Bearer` for API clients and tests. Login errors are identical for unknown email and wrong password. Roles are checked server-side (`require_roles`); the frontend hides admin-only UI but never relies on that for security. The token approach can later be replaced by Microsoft Entra ID without changing the endpoints' permission checks.

### TD-014 · Enquiry status: any change allowed, every change recorded (Phase 1)
Real workflows jump (e.g. straight to Cancelled), so there's no transition matrix yet. Every change writes `enquiry_status_history` (from, to, who, when, note). Phase 6 will set `proposal_generated` automatically.

### TD-015 · Enquiry references via a counter table
`reference_counters` (prefix, year) is incremented with `UPDATE … RETURNING`, which is atomic on SQLite and PostgreSQL. Numbers restart each year: `ENQ-2026-0001`.

### TD-016 · Styled native `<select>` instead of Base UI Select in forms
Native selects work directly with react-hook-form, are accessible and keyboard-friendly by default, and avoid Base UI Select's value/label API. Because options often load asynchronously, forms re-apply their value once options arrive (see `enquiry-form.tsx`).

### TD-017 · Next 16: auth boundary inside Suspense; pages set `instant = false`
`RequireAuth` uses `usePathname`, which Next 16 requires inside `<Suspense>` for prerendering. Authenticated pages wait for the browser-side session check, so each page in `app/(app)` exports `instant = false`. A layout-level setting did not silence the per-page dev validation.

### TD-018 · Same-origin API through a Next.js rewrite; LAN sharing on one port
The browser always calls `/api/v1/*` on the address it loaded the app from, and `next.config.ts` rewrites that to `BACKEND_URL` (default `http://127.0.0.1:8000`). Benefits: colleagues on the network need only port 3000; the backend never listens on the network; the session cookie is same-origin, so it works by IP address without CORS or SameSite issues. `NEXT_PUBLIC_API_BASE_URL` was removed. Shared mode (`scripts/start-shared.ps1`) uses the production server (`next start --hostname 0.0.0.0`), because the dev server blocks other hostnames and uses far more memory. The firewall rule covers Domain and Private profiles only. Plain HTTP is acceptable only on trusted networks; internet exposure requires HTTPS (cloud phase).

### TD-022 · Requirements: draft-friendly saves, reported (not enforced) completeness
Planners often capture requirements in several sittings, so `PUT` accepts partial data while still validating types, vocabularies and consistency. Completeness (`missing`) and conflicts (`warnings`) are computed on every read; the itinerary engine (Phase 4) will refuse to generate until `missing` is empty, and will surface the warnings. The enquiry summary (dates, travellers, budget) is synced from the requirements to keep lists and the dashboard consistent. The first save moves *New* enquiries to *In Progress*, recorded in the status history.

### TD-023 · Browser checks run in development mode too
Production builds hide React development warnings (a duplicate-key warning slipped through). Browser checks now also run against an isolated `next dev` server (`NEXT_DIST_DIR=.next-test`, separate ports and test database), so warnings are caught without disturbing the developer's own running app.

### TD-024 · Itinerary engine: deterministic heuristics, pure and explainable (Phase 4)
No LLM decides routes or picks inventory (PRD 13). The engine is a pure module over dataclasses (DB-free and fully unit-testable) and returns explanations and warnings with every plan. City selection scores sightseeing by customer interests and strategy affinity, strongly prefers cities with a hotel, and never drops a must-visit (an impossibility raises `GenerationError` with the reason). Routing uses nearest-neighbour plus 2-opt on great-circle distances with fixed arrival/departure ends. Nights go first to minimums, then to where unseen sightseeing and strategy affinity are highest. Hotel choice is a weighted score (stars, style, location, breakfast, room fit, group capacity), with price as the tie-breaker (cheapest for Classic/Scenic, highest-quality for Premium). The generated version stores the full report for transparency; editing (Phase 5) creates new versions rather than changing generated ones.

### TD-025 · Offline route map in the UI
Route maps are drawn as SVG from city coordinates (equirectangular projection), so they work without internet or tile services and are reusable in PDFs. Labels avoid overlapping earlier labels; a full map (Leaflet/OSM) can be added where online maps add value.

### TD-026 · Builder versioning: immutable snapshots plus one working copy (Phase 5)
Edits never touch saved versions. The latest version is either a locked snapshot (read-only) or the single working copy. *Start editing* clones the latest snapshot; *Save version* locks the copy; *Restore* clones any version as a new copy and auto-saves an open draft first, so nothing is lost. After structural day edits, stays and legs are re-derived from the days, keeping previous hotel and transport choices where they still apply, so totals, dates and the route can't drift. Warnings and costs are computed live from the version content rather than stored, so they always match the current edit.

### TD-027 · Controlled selects: read the event value synchronously
With React-controlled `<select>`s whose value only changes after the server responds, React restores the old DOM value immediately after `onChange`. Code must read `e.target.value` synchronously, not inside the async mutation callback. This was found by the builder's browser test (leg mode, vehicle and time of day were silently reverting) and fixed.

### TD-021 · Image pipeline and serving (Phase 2c)
Pillow validates by content (not the extension), caps pixels against decompression bombs, applies EXIF orientation and re-encodes, which drops all metadata including GPS (a privacy requirement for phone photos). The long edge is capped at 2400 px (enough for A4 brochures), plus a 480 px JPEG thumbnail. Dedupe uses SHA-256 of the original bytes. Files are served through authenticated API routes, with `?v=<hash>` URLs and `immutable` caching; replacing a file changes the hash, which busts caches. Uploads go through the Next.js rewrite like all other API calls (verified with real browser uploads).

### TD-019 · Login brute-force protection (in-memory lockout)
After 5 wrong passwords for an email within 15 minutes, that email is locked for 15 minutes (HTTP 429 `too_many_attempts`). It is keyed by email because behind the Next proxy all requests come from 127.0.0.1. State is in memory, which suits one local server process; a multi-instance cloud deployment must move it to the database or a cache.

### TD-020 · Remote access stays OFF on the company laptop
Remote access (Tailscale Serve via `scripts/start-tailscale.ps1`) was tested once and then disabled. It opens an extra network path into a company-managed laptop, which needs IT approval. Until a hosting decision is made, the app runs locally only (`127.0.0.1`). Options for later: Tailscale (with IT approval and ACLs limited to HTTPS only) or cloud hosting under YANA DMC's own account.
