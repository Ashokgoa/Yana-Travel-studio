# YANA Travel Studio – PRD (summary)

> Condensed working summary of the full PRD / technical specification (Parts 1–29). Store the original full document alongside this file as `docs/PRD_FULL.md`; it remains the authoritative source.

## Vision
A B2B tool for YANA DMC planners: enter travel-agent requirements, generate **three itinerary alternatives** from a structured inventory, customise one, and download a **branded, image-rich PDF proposal**. Target: about 10–15 minutes when inventory is sufficient (a target to validate, not a guarantee).

## Users
- **Administrator**: inventory, suppliers, images, PDF templates, pricing configuration, settings.
- **Travel Planner**: enquiries, requirements, itinerary generation and editing, costing, PDF proposals, versions.
- Designed to add Sales, Operations and Finance roles later.

## Modules (sidebar order; unimplemented modules hidden)
Dashboard · CRM (Agents, Customers, Enquiries) · Itinerary Builder (Create, Saved, Templates, Compare) · Destination Inventory (Countries, Cities, Sightseeing, Hotels, Restaurants, Transportation) · Suppliers · Pricing & Costing · PDF Designer · Bookings · Administration

## Non-negotiable rules
1. Itineraries are built from **structured inventory + deterministic rules**, not invented by an LLM. AI is optional and assistive.
2. Never invent prices, availability or bookings. Costs are **"Estimated"** unless verified by supplier quotations.
3. Never assume dietary availability (Jain, halal, vegetarian…) without verified inventory data.
4. Route distances and times are labelled as estimates unless verified. Straight-line distance is not driving distance.
5. Mandatory destinations are never silently dropped. The engine explains what doesn't fit.
6. Day and night totals must match the request and be internally consistent.
7. Itineraries **reference** inventory records; they never copy them.
8. **Customer-facing views and PDFs never show supplier costs or margins.**
9. AI-generated images are flagged as illustrative and never used to represent a real property.
10. Don't invent or recreate the YANA DMC logo; the business uploads it.
11. Demo data is clearly labelled as demonstration data.
12. AI never overwrites a saved itinerary without user approval.
13. No paid services without approval; the local app works fully offline from cloud services.

## Key capabilities by phase
| Phase | Scope |
|---|---|
| 0 | Foundation: structure, FastAPI, Next.js, SQLite, Alembic, config, scripts, docs |
| 1 | Dashboard, sidebar, roles, travel agents, customers, enquiries (8 statuses) |
| 2 | Countries, cities, sightseeing, hotels (+ room types, seasonal rates), restaurants, vehicles, suppliers, central image library (upload, primary, reorder, replace, delete) |
| 3 | 9-step requirement form: customer, travel, destinations (mandatory/optional/avoid), interests, hotels, food, transport, budget, notes |
| 4 | Engine: validate → destinations → attractions → route → nights → hotels → restaurants → transport → costs → 3 strategies (Classic, Scenic, Premium) |
| 5 | Day-by-day editor: add/remove/duplicate days, move activities (drag-and-drop plus accessible up/down), replace hotel/restaurant/transport, versions (save, duplicate, restore, compare) |
| 6 | PDF: YANA Classic / Premium / Explorer templates, cover, overview, route map, daily pages, hotel and sightseeing sections, inclusions/exclusions, T&Cs; image overrides, section visibility and order, live preview; A4, page numbers; file name `YANA_<Tour>_<Customer>_V<n>.pdf`, linked to the version |
| 7 | Pricing: hotel, coach, transfers, tickets, guides, meals, other; bases per person/room/day/vehicle/group; margin %, discounts, adjustments; internal vs customer views |
| 8 | AI provider abstraction, natural language → requirements, suggestions as reviewable changes, optional image generation |

Also required: itinerary templates (e.g. EURODIA Grand Tour 12 days; not hardcoded), database backup and restore, image metadata export, automated tests (20 business scenarios in PRD Part 25).

## MVP acceptance scenario (PRD Part 28)
15 days · 4 adults + 2 children · 6 countries · arrive Amsterdam, depart Zurich · 4★ · Indian vegetarian · private coach · scenic · €3,000 pp. The whole flow, from agent record to downloaded branded PDF with internal pricing hidden and the version saved, runs locally without paid infrastructure.

## Initial countries
Netherlands, Belgium, France, Germany, Luxembourg, Switzerland, Austria, Italy (configurable; 2–4 cities, 3–5 attractions, 2–3 demo hotels, 1–3 demo restaurants each).
