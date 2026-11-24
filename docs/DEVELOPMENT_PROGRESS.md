# Development Progress

| Phase | Name | Status |
|---|---|---|
| 0 | Project foundation | ✅ Complete (2026-11-23) |
| 1 | UI foundation & CRM | ✅ Complete (2026-11-23), awaiting approval |
| 2 | Destination inventory & images | ✅ Complete (2026-11-24) |
| 3 | Customer requirement capture | ✅ Complete (2026-11-24) |
| 4 | Itinerary engine | ✅ Complete (2026-11-24) |
| 5 | Visual itinerary builder | ✅ Complete (2026-11-24) |
| 6 | PDF designer | ✅ Complete (2026-11-24) |
| 7 | Pricing & costing | ✅ Complete (2026-11-24) |
| 8 | AI assistant (offline first) + housekeeping | ✅ Complete (2026-11-24), awaiting approval |

---

## Phase 8d – Day-by-day planning by hand, PDF text and photos, Grand Tour template (2026-11-24, from YANA's feedback)

YANA feedback: the planner builds the itinerary day by day (city, sightseeing, photos, restaurants, hotels); the app may propose itineraries but must not impose them; then the itinerary is previewed and turned into a PDF with images and logo. The reference brochure should become a template, and the PDF wording should be editable with an immediate preview.
- **Create itinerary** (enquiry page, and the *Create Itinerary* menu page): name, start date, number of days and first city (prefilled from the requirements). A *Day by day* draft opens straight in the builder (no generation, editable at once). *Suggest itineraries* (the engine) is now the secondary option, next to *From a template*.
- **Builder: "Day in" and "Overnight in" pickers on every day.**
  - Stays, hotels, travel legs, and the check-out / "Travel to …" / check-in lines follow automatically.
  - "Day in" moves the night too when both were the same city; "Overnight in" changes only the night (so a day trip is "Day in Lucerne, Overnight in Paris").
  - Cities with sightseeing on the way are kept, with two legs (Amsterdam → Brussels → Paris).
  - Automatic day titles follow the plan ("Amsterdam → Paris" on travel days); planners' own titles are kept.
  - Hotels are the planner's choice (*Replace* on each stay).
- **PDF designer**:
  - *Day-by-day text*: heading, subtitle, bullet points (`**bold**`), meals line and note per day. Each starts from the automatic text, the preview updates as you type, and the itinerary itself is not changed.
  - *Photos*: upload from the computer or pick from the image library, for the cover and for each day. A chosen cover photo shows on every template.
  - Stored in `proposal_settings.day_texts` and `cover_image`.
- **Route on the PDF**: day excursions from a base (Lucerne from Zurich) are no longer route stops; their countries still count.
- **Templates keep their PDF design** (texts and photos) and pass it to proposals created from them.
- **Template import** (`python -m app.cli import-template FILE.json`, `services/template_import.py`):
  - Builds a template from a structured description: days with city, overnight city, sightseeing (matched to inventory, otherwise custom) and meals.
  - Can add missing cities and sightseeing to inventory, picks hotels by stars, and stores the PDF wording.
  - **"European Grand Tour"** (the reference brochure: 12 days, 6 countries, Amsterdam → Brussels → Paris → Luxembourg → Cochem → Zurich) was imported into YANA's database, after a backup. It added Cochem and Reichsburg Castle to inventory. The description file is kept outside the repository (`Downloads\Yana\Samples`).
- Tests: 6 backend (blank itinerary, planning cities and the day/night rule, day texts and cover, templates keeping PDF texts, template import with cities on the way). Browser flow: 14 checks, zero warnings.

## Phase 8c – Itinerary first, supplier prices (2026-11-24, from YANA's testing feedback)

YANA feedback: agents ask for an itinerary for N days first; costs depend on season and supplier, so budget comes later. Each cost should be priced from a chosen supplier, with the price editable, before YANA's markup is added. TourBrain (an Indian travel CRM) was reviewed for ideas: plan first, then the quote; supplier prices entered, not fetched; markup on cost.
- **Budget is optional.** A missing budget no longer blocks *Generate*; it shows as a reminder instead. When something else is missing, the enquiry page lists it with a link to the right wizard step (previously only a hover tooltip).
- **Supplier rate cards** (`supplier_rates`, migration `0009`): each supplier's prices per service, by category and basis, in any currency, optionally per season. Shown on the supplier page (add, edit, remove).
- **Supplier price per cost line** (*Price* button on the pricing sheet):
  - Pick a supplier and its rates pop up (season-valid ones first, others marked "Other season"). Click a rate to fill the price, then edit it if needed.
  - Choose the currency (CHF, GBP… converted at a rate you type, remembered per sheet), the status (*Estimate / Quoted / Confirmed*) and a reference ("email 24 Nov").
  - Optionally save a typed price to the supplier's rate card.
  - Lines show the supplier (from inventory by default), the status badge and the original currency. A progress bar shows "N confirmed · N quoted · N estimates". Quotes carry over to new versions.
- **Markup** is unchanged: margin % per category (plus adjustment per person, discount, rounding) on top of the supplier costs.
- **Bug found by the browser test**: the supplier list in the price dialog asked for 200 suppliers per page (the API maximum is 100), so it stayed empty; fixed.
- Tests: 4 backend (rate cards, quote in CHF with saved rate, status and progress, extra line saved to the rate card, quotes follow versions, generating without a budget), browser flow 11 checks, zero warnings.

Next ideas (not built): 3★/4★/5★ options in one quote, sending the quote to the agent, requesting rates from suppliers by email.

## Phase 8 – AI assistant (offline first) and housekeeping (2026-11-24)

YANA decision (2026-11-24): build both. AI is offline by default on the company laptop; the optional Claude connection stays **off** until IT approves it.

### AI assistant (8a)
- **Offline requirement reader** (`engines/text_extract.py`, pure rules, no network). It reads:
  - travellers, children's ages, and "family of / group of / pax" totals;
  - dates in many formats and trip lengths (15 days, 12D/11N, 7 nights);
  - arrival and departure places, and countries and cities from inventory, including aliases (Holland, Swiss, Benelux);
  - hotel stars and style, rooms, food (veg, Jain, non-veg, halal, vegan), meals (including half and full board), interests, pace, transport and GIT/FIT;
  - budget per person or total in EUR, INR (lakh grouping), USD, GBP or CHF, and special requests (wheelchair, anniversary…).
  - Places not in inventory are reported, and every value comes with the quote it was read from.
- **Providers**: `OfflineProvider` (default) and `ClaudeProvider`.
  - Claude uses the `anthropic` SDK 2.13 (`messages.parse` with a Pydantic schema, model `claude-opus-5-5`). It is used only when `YANA_AI_PROVIDER=claude` and the SDK is installed (`backend/requirements-ai.txt`).
  - Any error, refusal or missing connection falls back to the offline reader and tells the planner.
- **Read from email** in the requirements wizard:
  - Proposed values come with quotes. A value that conflicts with existing data is shown as "Replaces: …" and left unticked.
  - The wizard merges the chosen values into the form (replace, union for lists, append for destinations and notes). Nothing is saved until the planner saves.
- **Itinerary suggestions** (`services/itinerary_suggestions.py`, inventory rules only): remove a duplicate visit; move or remove a visit on a closed weekday; remove sightseeing unsuitable for children; use a restaurant with a verified diet option; fill an empty free day with matching open sightseeing; use a hotel of the requested category. Each has a stable key and is applied with **Apply**, through the builder's own edit operations on a working copy (versioned).
- **Administration → AI assistant**: shows what is active, whether data leaves the computer, and how to switch Claude on (with IT approval).

### Housekeeping (8b)
- **Backups** (`services/backup_service.py`): one zip holding a consistent SQLite snapshot (online backup API, safe while the app runs), the uploads, the PDFs and a manifest (revision, counts).
  - Admin page: *Back up now*, download, delete.
  - Command line: `scripts\backup.ps1`.
- **Restore** (`scripts\restore.ps1 -File …`, command line only, app stopped):
  - It validates the zip (manifest, no unsafe paths, SQLite integrity) and refuses while the database is open.
  - It takes a `before-restore` safety backup, clears stale WAL files, replaces the database, uploads and exports, then runs the migrations.
- **Itinerary templates** (`kind="template"`, no enquiry):
  - *Save as template* from any itinerary; the *Itinerary Templates* page lists templates (View, Archive).
  - *From a template* on an enquiry copies a template, moves the dates to the customer's arrival date and re-prices the rooms for the new dates.
  - Templates are excluded from Saved Itineraries.
- **Remove demo data**: only `is_demo` inventory (hotels with their rooms and rates, restaurants, vehicles, suppliers, demo sightseeing). Records still used by itineraries are deactivated, not deleted; image links are dropped but the images stay in the library.

### Tests
- **Backend:** 16 new tests (reader variants, mapping, provider fallback, suggestions and apply, backups API, restore round trip and safety backup, invalid and unsafe zips, refusal while in use, demo removal, templates). 170 in total.
- **Frontend:** 2 new (merging read values). 9 in total.
- **Real browser, development mode:**
  - AI flow: 14 checks.
  - Housekeeping flow: 17 checks.
  - Zero console warnings.
- **Restore** was also run through the command line, both with the app running (refused) and stopped.

### Known limits
- The offline reader is rule-based: unusual wording can be missed, so the planner always reviews before saving. Claude reads better but needs IT approval.
- Suggestions don't invent sightseeing or restaurants; they only use what is in inventory.
- Restore from the browser is deliberately not offered.

## Phase 7 – Pricing & costing (2026-11-24)

YANA decisions (2026-11-24): a margin per service category; prices shown per adult twin sharing plus single supplement and child prices; EUR with an optional second currency at a manually entered rate; admins and planners see costs.

### Backend (7a)
- **Pricing engine** (`engines/pricing.py`, pure):
  - Shared costs (coach, driver, guides, group extras) are divided by all travellers. Per-person costs (tickets, meals, train fares) count once per traveller.
  - The adult twin price includes half a double room per night. The single supplement is the single rate minus that half (the double rate is used when there is no single room type, flagged as an estimate).
  - A child without a bed pays no hotel share; a child with a bed pays an adjustable % of it.
  - Each part gets its category's mark-up. Then the discount %, an adjustment per person and rounding up are applied.
  - Group revenue (prices × travellers) is compared with the **actual** cost of every line (the real room plan) to give profit and the margin on revenue.
- **Pricing sheet per version** (`pricing_sheets`, `pricing_lines`, migration `0008`):
  - Automatic lines are rebuilt from the version on every read: hotel rooms, vehicle and driver, train legs (no price yet), tickets, restaurant meals, and lunch or dinner at hotels (no price yet).
  - The sheet stores only the planner's decisions: margins, discount, adjustment, rounding, traveller split, overrides of automatic lines by stable key, room-rate overrides, extra lines, the display currency, exchange rate and PDF currency, and notes.
  - It follows the content to new versions (start editing, restore, duplicate).
- **Unknown costs** are listed as "No price" and the prices are flagged as incomplete; nothing is guessed. Inventory prices in another currency are left out with a warning.
- **Admin defaults** (`/settings/pricing`): margin per category (15% placeholder with a "not reviewed" warning), rounding, child bed share, display currency and rate.
- **PDF**: the price section shows selling prices from the sheet (adult twin, single supplement, children) in EUR, the other currency, or both. A price typed in the designer still wins. Each export stores a snapshot of the price shown.
- 12 tests: the engine maths checked by hand, the API, versions, and no costs, profit or margin in proposals.

### Frontend (7b)
- **Pricing sheet** (`/itineraries/{id}/pricing`, from *Pricing* on the itinerary page and in the builder):
  - Selling-price tiles, with the other currency.
  - Internal figures: cost per adult, revenue, cost, profit, margin on revenue, and the customer's budget.
  - Cost lines grouped by category, with include, editable cost and quantity, Estimate / No price / Edited / Added badges, *Back to inventory values*, and *Add cost line*.
  - Room rates (double and single) used for the per-person prices.
  - Side panels: margins (with per-person cost → selling for each category), discount, adjustment, rounding, child bed share, travellers, currency and internal notes.
- **Pricing & Costing** menu page and **Administration → Pricing defaults**.
- The PDF designer's price panel shows the calculated price with a link to Pricing; the typed price is now an optional override.
- Real browser, **development mode**: 23 checks pass with zero console warnings. They cover:
  - changing a margin, overriding a line and resetting it, adding a line through the dialog;
  - rounding (a select), a single room, the INR rate and the PDF currency;
  - the PDF preview showing selling prices but no cost, profit or margin;
  - the admin defaults, the list page and the menu.

### Known limits
- Ticket and meal prices are often missing in the demo inventory, so the prices show as incomplete until those costs are entered (in inventory or on the sheet).
- There are no infant rules or age bands yet: every child is either "with bed" or "without bed".
- Exchange rates are typed in (no live rates), by design.

## Phase 6 – PDF designer (2026-11-24)

Modelled on YANA's reference proposal (12-page "European Grand Tour", kept outside the repository). Its layout is reproduced and filled automatically from each itinerary; none of its text or photos are copied.

### Backend (6a)
- **Offline route map** (`engines/route_map.py`): Natural Earth borders and flag-icons flags are bundled (`backend/app/assets`, licences in `LICENSES.md`). Visited countries are coloured, with a dashed route and arrows, pins and labels, round photos, arrival and departure planes, a legend with flags, a compass and a scale bar. No tiles or internet are used.
- **Document builder** (`services/proposal_content.py`):
  - Cover: title, "N Countries · D Days · N Nights", introduction.
  - Tour highlights: destinations, group size, duration, hotels, meals, transport, tour style (GIT/FIT).
  - Route text and map.
  - Day by day: heading with flags, date, photo, subtitle, bullets with places in bold, meals line, the planner's day note.
  - Hotels, the country-and-day summary table (with "no overnight stay"), price, inclusions and exclusions, terms, closing message and contacts.
- **Templates** (`templates/proposal/proposal.html.j2`):
  - **Classic**, like the reference PDF.
  - **Premium**: full-page photo cover, serif headings, one day per page.
  - **Explorer**: timeline with photos beside the text.
  - The same HTML drives the live preview and the PDF. Page numbers come from CSS `@page` margin boxes.
- **Customer-safe output**: no supplier names, costs, margins, internal notes or engine planning notes appear. The only price is the selling price the planner types in; otherwise the PDF shows "Price on request".
- **Branding per export**: travel agent (white label), YANA, or both. Admins set the YANA logo, colours, contact line and default closing, exclusions and terms.
- **Export**: Playwright prints with the installed **Microsoft Edge** (falling back to Chrome), so no browser download is needed. The page has JavaScript off and no network access.
  - An open working draft is saved first as a read-only version named "PDF proposal".
  - The file is saved as `exports/itineraries/<uuid>.pdf` and downloads as `YANA_<Tour>_<Customer>_V<n>.pdf`.
  - Each export is recorded in `proposal_exports`, with the version and settings used.
  - The enquiry moves to *Proposal generated* (only from New, In progress or Revision requested).
- Migration `0007`. 12 new tests, including a real Edge render (A4, at least 3 pages, page numbers).

### Frontend (6b)
- **PDF designer** (`/itineraries/{id}/proposal`, opened from *PDF proposal* on the itinerary page or *PDF* in the builder):
  - Settings: template, branding, colours, sections (on/off and order), price and note, title, introduction and closing (automatic until edited), hotel names in the day text, a photo choice per day (automatic, none, or any photo of that day's sightseeing, hotel or city), inclusions, exclusions and terms.
  - The live preview refreshes about 0.5 s after each change, in a sandboxed iframe.
  - *Save settings*; *Create PDF* downloads the file; a list shows the PDFs already created.
  - The internal cost estimate is shown to the planner only, clearly marked as never in the PDF.
- **PDF Designer** menu item: pick an itinerary to design.
- **Administration → Branding & PDF**: logo upload, colours, contact line and default texts, with a warning until the placeholder terms are replaced and marked as reviewed.
- Real browser, **development mode**: 23 checks pass with zero console warnings. They cover:
  - opening from the itinerary page, agent branding, "Price on request" and the embedded photo;
  - the Premium cover, Both branding, the price, switching a section off, reordering, a custom introduction and the photo choice;
  - save and reload, creating the PDF (a real Edge render, about 300 KB), the enquiry status, the branding page and the menu.

### Known limits
- The default terms are a short placeholder: YANA must replace them (the admin page warns until this is done).
- Agent logos are not supported yet; agent branding uses the agent's name and contact details.
- The preview shows page breaks as dashed lines; exact pagination is only visible in the PDF.
- A PDF takes about 10 to 15 seconds, mostly Edge starting on this laptop.

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
