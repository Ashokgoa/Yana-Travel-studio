# Development Plan & Specification Analysis

This file holds the "first action" analysis required by PRD Part 29. Status of each phase is tracked in [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md); decisions are in [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md).

## 1. Technical dependencies

| Area | Dependency | Version (Nov 2026) | Notes |
|---|---|---|---|
| Runtime | Python | 3.11.9 | Installed. `backend/.venv` |
| Runtime | Node.js / npm | 24.14 / 11.9 | Installed |
| Backend | FastAPI, Starlette, Uvicorn | 0.165 / 1.10 / 0.54 | |
| Backend | SQLAlchemy, Alembic | 2.1 / 1.20 | SQLite now, PostgreSQL later |
| Backend | Pydantic, pydantic-settings | 2.14 / 2.16 | Env-based config (`YANA_*`) |
| Frontend | Next.js (App Router), React | 16.4 / 19.3 | Next 16 differs from older docs; bundled docs in `node_modules/next/dist/docs` |
| Frontend | Tailwind CSS, shadcn/ui (base-nova, Base UI) | 4.3 / CLI 4.23 | shadcn now builds on `@base-ui/react`, not Radix |
| Frontend | lucide-react | 1.x | Icons |
| Frontend | Vitest | 5.x | Unit tests |
| Phase 1 | `pwdlib[argon2]` or `bcrypt` | – | Password hashing (if login is required) |
| Phase 2 | Pillow | – | Image validation, dimensions, compression, thumbnails |
| Phase 2+ | TanStack Query, React Hook Form + Zod, TanStack Table | – | Data fetching, forms, tables |
| Phase 4 | (none required) | – | Route estimates computed locally; optional OSRM later |
| Phase 5 | dnd-kit | – | Drag-and-drop with keyboard support |
| Phase 6 | Playwright (Python) + Chromium **or installed Microsoft Edge** | – | PDF rendering; Jinja2 for HTML templates |
| Phase 6 | Leaflet + OpenStreetMap tiles | – | Interactive maps in the UI; PDF route map rendered as SVG (see risks) |
| Phase 8 | AI provider SDK (e.g. Anthropic) | – | Optional; app works without it |

## 2. Architectural risks and mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **Playwright cannot download Chromium** on a corporate network/proxy | PDF generation blocked | Spike in Phase 6 day 1. Fallback: Playwright `channel="msedge"` uses the Edge already installed on Windows, no download needed |
| R2 | **Maps in PDFs**: Leaflet needs live OSM tiles; OSM tile policy discourages automated bulk use; headless render timing is fragile | Blank or slow maps | Render the PDF route map as an **offline SVG** from city coordinates (country outlines from public-domain Natural Earth data). Use Leaflet only in the interactive UI, with attribution |
| R3 | **Driving distances**: no free, reliable, offline routing API | Wrong travel times | Great-circle distance × road factor (≈1.25), average coach speed, always labelled **"Estimated"**. Planner can override with verified values. Optional OSRM integration later |
| R4 | Itinerary engine scope creep (it is effectively a constrained optimisation problem) | Delays, unpredictable output | Deterministic heuristics: ordered route via nearest-neighbour + 2-opt between fixed start/end, rule-based night allocation, scored inventory matching. Every output is explainable, and conflicts are reported, never silently dropped |
| R5 | Version management: deep-copying a version (days, activities, hotels, transport, pricing, image choices) | Data inconsistency | One `clone_version()` service with tests. Versions become read-only once a PDF is generated |
| R6 | Polymorphic media associations have no DB-level foreign key | Orphan links | `media_links` written only via the media service. Inventory deletes are soft (deactivate). A cleanup job and a test cover it |
| R7 | Exposing internal costs/margins in customer PDFs (business-critical) | Commercial damage | Separate customer-facing DTOs that **structurally exclude** cost fields (not just hidden in templates). Automated test greps the rendered customer PDF HTML for cost values |
| R8 | Inventory quality drives output quality; demo data could be mistaken for real | Bad proposals | `is_demo` flag on every inventory row, shown as a badge. Prices default to `is_verified = false` and are labelled "Estimated" |
| R9 | `next/font/google` downloads fonts at build time | Offline build fails | Acceptable for now. Self-host fonts in Phase 6 (needed anyway for PDF embedding) |
| R10 | SQLite concurrency | Single-user only | Fine for the local MVP. SQLAlchemy and Alembic keep the PostgreSQL move a config change |
| R11 | Newest framework majors (Next 16, shadcn on Base UI, Starlette 1.x) | Fewer online examples | Read bundled docs and pin versions |

## 3. Final project structure

Implemented as specified in PRD 4.2, with small additions:

```
yana-travel-studio/
  backend/            FastAPI app (api → services → repositories → models), engines/, tests/
    alembic.ini       points at ../database/migrations
  database/
    migrations/       Alembic env + versions
    seed/             demo inventory loaders (Phase 2)
    yana_studio.db    local SQLite (git-ignored)
    backups/          (git-ignored)
  frontend/           Next.js: app/, components/{ui,layout}, features/<module>/, hooks/, services/, types/, tests/
  uploads/<category>/ local image storage (git-ignored, keys stored relative)
  backend/app/templates/proposal/   (Phase 6: one HTML template, Classic / Premium / Explorer styles)
  exports/itineraries/ generated PDFs (git-ignored)
  docs/  scripts/  README.md  CLAUDE.md
```

## 4. Initial database schema

See [DATABASE_DESIGN.md](DATABASE_DESIGN.md). Phase 0 migrates `roles`, `users` and `app_settings`. Each later phase adds its own tables through a new Alembic revision.

## 5. Implementation milestones

| Phase | Milestone | Key acceptance checks |
|---|---|---|
| 0 | Foundation | Both apps start; DB migrates; `/docs` reachable; tests pass ✅ |
| 1 | UI foundation, roles, CRM (agents, customers, enquiries + status workflow), dashboard counters | CRUD, search and filter; enquiry status transitions; role-gated UI ✅ |
| 2 | Inventory (countries → cities → attractions/hotels/restaurants, suppliers, vehicles), central media library, demo seed | Add a country/city without code changes; multi-image upload, reorder and primary; path-traversal and size tests |
| 3 | Multi-step requirement capture (9 steps, draft autosave) | Structured requirements saved and reloaded exactly |
| 4 | Itinerary engine: validate → destinations → route → nights → attractions → hotels → restaurants → transport → cost estimate → 3 strategies | PRD business test cases 1–10 and 15; day/night consistency; mandatory destinations never dropped |
| 5 | Visual builder: day cards, activities, replace hotel/restaurant/transport, DnD + keyboard moves, versions (save, duplicate, restore, compare) | Test cases 11–14, 16–17 |
| 6 | PDF designer: 3 templates, branding, image overrides, live preview, Playwright render, download | Test cases 18–20; no clipping or overlap; page numbers |
| 7 | Pricing engine: cost lines by basis, margin, discounts, per-person and group totals; internal vs customer views | Pricing math tests; customer views contain no costs |
| 8 | AI layer (optional): provider interface, NL → requirements, suggestions as reviewable diffs | Inventory-only recommendations; no auto-overwrite |

**Suggested ordering note:** Phase 7 (pricing) comes after Phase 6 (PDF), but the PDF needs a pricing section. Phase 6 will render a pricing block whose visibility is controlled by a flag, and Phase 7 fills it in. Alternatively, swap Phases 6 and 7. This is the business's call.

## 6. Missing business decisions (need YANA DMC input)

**Branding and content**
1. Official **logo files** (colour and white variants, SVG/PNG), **brand colours** (hex) and **fonts**. The UI currently uses a clearly marked placeholder palette.
2. Contact block for PDFs (email, phones, address, VAT/CoC lines?) and which legal lines appear on proposals.
3. Standard **inclusions / exclusions** and **terms & conditions** text, and whether they vary by template or market.
4. Proposal language(s): English only for the MVP?
5. Can you provide the **EURODIA European Grand Tour** reference itinerary (PDF/Word) to model templates and PDF content against?

**Commercial**

6. **Base currency** (EUR?) and whether proposals need other currencies (INR, USD), plus the exchange-rate source.
7. **Default margin %**: single, per agent, or per service category? Rounding rules for selling prices?
8. **Price presentation**: per person twin-sharing, single supplement, child-with-bed / child-without-bed, infant rules and age bands.
9. Who may see internal costs: Planner and Admin (assumed), or Admin only?

**Operational rules for the engine**

10. Default **travel pace**: minimum nights per city, maximum coach driving hours per day (EU driver-hours rules: 9 h/day driving and a 45-min break after 4.5 h). Should the engine enforce these?
11. Coach costing conventions: driver accommodation and meals, empty-leg / repositioning costs, city tolls and parking.
12. Hotel **seasons**: fixed calendar seasons or per-hotel date ranges?
13. Typical group sizes for FIT vs GIT, and room-allocation rules (twin/triple, children sharing).

**Platform**

14. ~~Login for the local MVP?~~ **Decided:** real login with roles (Phase 1).
15. ~~Enquiry ID format~~ **Decided:** `ENQ-2026-0001`, yearly sequence.
16. **Image rights**: are supplier/stock photos licensed for use in proposals? Any approved stock source?
17. Should demo data be removable in one click once real inventory is loaded?

## 7. Assumptions made until decided

EUR base currency · English only · Admin and Planner both see internal costs (customer PDFs never do) · real login with Admin/Planner roles (decided) · placeholder brand palette · route distances are estimates.
