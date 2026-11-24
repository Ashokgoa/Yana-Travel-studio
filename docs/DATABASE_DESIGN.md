# Database Design

Relational schema managed by SQLAlchemy 2 + Alembic. SQLite locally; portable to PostgreSQL (no SQLite-only SQL, JSON columns via SQLAlchemy `JSON`, naming conventions for constraints, `render_as_batch` migrations).

**Conventions**
- Every table: integer `id` PK, `created_at`, `updated_at` (UTC, timezone-aware).
- FKs are indexed. Deletion rules: inventory and CRM rows are **soft-deleted** (`is_active=false`) because itineraries reference them; child rows owned by a parent (days → activities) use `ON DELETE CASCADE`; references to inventory from itineraries use `RESTRICT`.
- Money: `Numeric(12,2)` + `currency` (ISO 4217). Prices carry `is_verified` (false = indicative/estimated).
- Multi-select enum preferences (interests, food types…) are stored as JSON arrays of **validated enum codes** (validated by Pydantic). Destinations, which need FKs, get proper link tables.
- Demo data: `is_demo` flag on inventory and supplier rows.

Status legend: ✅ migrated · others planned (phase in heading)

## Platform

| Table | Key columns | Status |
|---|---|---|
| `roles` | code (unique: `admin`, `planner`), name, description | ✅ P0 (seeded) |
| `users` | email (unique), full_name, password_hash (nullable until auth), is_active, role_id → roles (RESTRICT) | ✅ P0 |
| `app_settings` | key (unique), value JSON, description. Holds branding, default margin, T&Cs, contact block | ✅ P0 |

## CRM (Phase 1) ✅ migration `0002`

| Table | Key columns |
|---|---|
| `travel_agents` | company_name (idx), contact_person, email (idx), phone, country (free text, idx; agents may be outside Europe), address, company_details, internal_notes, status (`active`/`inactive`, idx) |
| `customers` | travel_agent_id → travel_agents (RESTRICT, nullable = direct customer), name (idx), phone, email, nationality, country_of_residence, adults, children, children_ages JSON[int], special_requirements, is_active |
| `enquiries` | reference (unique, `ENQ-YYYY-NNNN`), travel_agent_id → (RESTRICT), customer_id → (RESTRICT), enquiry_date, travel_start_date, travel_end_date, adults, children, destination_preferences (free text until Phase 3), budget_amount Numeric(12,2), budget_currency, budget_basis (`per_person`/`total`), status (8 PRD values, idx), assigned_planner_id → users (SET NULL), internal_comments |
| `enquiry_status_history` | enquiry_id → (CASCADE), from_status, to_status, changed_by_id → users (SET NULL), note, created_at |
| `reference_counters` | prefix, year, last_value · unique(prefix, year). Atomic `UPDATE … RETURNING` increment for references |

Rules enforced in services: a customer linked to agent A can't appear on an enquiry for agent B; new customers or enquiries can't be created for inactive agents; children_ages length must equal children (ages 0–17).

## Requirements (Phase 3) ✅ migration `0004`

| Table | Key columns |
|---|---|
| `enquiry_requirements` (1:1 enquiry) | arrival_date, departure_date, total_days, total_nights, arrival_airport, departure_airport, start_country_id, end_country_id, travel_type (FIT/GIT), group_size, adults, children, children_ages, interests JSON, hotel_categories JSON, hotel_location_prefs JSON, breakfast_required, room_types JSON, rooms_count, food_preferences JSON, meal_plan (enum), selected_meals JSON, transport_modes JSON, luggage_notes, airport_transfers, local_transport, budget_per_person, budget_total, currency, budget_flexibility (enum), travel_class, additional_requirements, internal_notes |
| `enquiry_destinations` | requirement_id → (CASCADE), country_id → (RESTRICT), city_id → (nullable), preference (mandatory / preferred / optional / avoid), min_nights, sort_order |

As built: `rooms` is JSON `[{type, count}]`, `meals` a JSON list, plus `travel_pace`, `completed_steps` and `updated_by_id`. Totals (days, nights, room capacity), `missing` and `warnings` are computed when read, not stored.

## Destination inventory (Phase 2) ✅ migration `0003`

| Table | Key columns |
|---|---|
| `countries` | name, iso_code (unique), region, description, is_active, sort_order |
| `cities` | country_id →, name, description, latitude, longitude, recommended_nights_min/max, is_active · unique(country_id, name) |
| `suppliers` | name, supplier_type (hotel, coach, restaurant, guide, attraction, other), contact_name, email, phone, country_id →, address, notes, is_demo, is_active |
| `attractions` | city_id →, name, category, interest_tags JSON, description, recommended_duration_min, opening_hours JSON, operating_days JSON, ticket_required, ticket_price, currency, price_is_verified, seasonal_info, child_friendly, setting (indoor/outdoor/mixed), latitude, longitude, supplier_id →, is_demo, is_active |
| `hotels` | city_id →, name, star_rating, style_tags JSON (boutique, luxury, budget), location_type (city_centre, airport, suburban, resort), description, address, latitude, longitude, breakfast_available, facilities JSON, parking, group_capacity_rooms, supplier_id →, contact_email, contact_phone, is_demo, is_active |
| `hotel_room_types` | hotel_id → (CASCADE), name, max_occupancy, bed_config, base_price, currency, price_is_verified |
| `hotel_rates` | hotel_id →, room_type_id →, season_name, valid_from, valid_to, price, currency, basis (per_room_night), is_verified |
| `restaurants` | city_id →, name, cuisine, description, address, latitude, longitude, **vegetarian / jain / halal / vegan / non_vegetarian: nullable booleans (NULL = unknown, never assumed)**, group_capacity, price_range, avg_price_per_person, currency, price_is_verified, opening_hours JSON, supplier_id →, contact_*, is_demo, is_active |
| `vehicle_categories` | code (7_seater … luxury_coach), name, passenger_capacity, luggage_capacity |
| `vehicles` | category_id →, supplier_id →, name, service_types JSON (airport_transfer, local, intercity, long_distance), price_per_day, price_per_km, driver_cost_per_day, additional_costs JSON, currency, price_is_verified, availability_notes, is_demo, is_active |
| `vehicle_countries` | vehicle_id →, country_id → (operating countries) |

## Media (Phase 2) ✅ migration `0003`

| Table | Key columns |
|---|---|
| `media` | storage_key (relative, unique), original_filename, mime_type, size_bytes, width, height, sha256 (unique, dedupes identical uploads), category, source (upload, supplier, ai_generated, stock), description, alt_text, is_ai_generated, is_illustrative, uploaded_by → users |
| `media_links` | media_id → (CASCADE), entity_type (country, city, attraction, hotel, restaurant, vehicle, supplier, brand), entity_id, is_primary, sort_order, caption · unique(entity_type, entity_id, media_id) |

The polymorphic `media_links` lets one image serve many records without duplicating files. Integrity is enforced by the media service (see risk R6).

## Itineraries (Phases 4–5) ✅ migration `0005`

| Table | Key columns |
|---|---|
| `itineraries` | kind (proposal / template), enquiry_id → (nullable for templates), title, strategy (classic, scenic, premium, custom), status, current_version_id, is_archived, created_by |
| `itinerary_versions` | itinerary_id → (CASCADE), version_number (unique per itinerary), label ("Hotel upgrades"), notes, start_date, total_days, total_nights, is_locked (true once a PDF is generated), generation_report JSON (engine warnings/explanations), created_by |
| `itinerary_days` | version_id → (CASCADE), day_number, date, city_id → (overnight city), title, description, is_free_day |
| `itinerary_activities` | day_id → (CASCADE), sort_order, time_slot (morning, afternoon, evening, full_day), activity_type (sightseeing, transfer, meal, check_in, check_out, free_time, custom), attraction_id → (nullable, RESTRICT), title, description, duration_min |
| `itinerary_hotels` | version_id → (CASCADE), hotel_id → (RESTRICT), room_type_id →, city_id, check_in_day, nights, rooms, room_config JSON, is_alternative |
| *As built* | Tables are `itinerary_meals` (per day: meal, arrangement hotel/restaurant/own, restaurant_id, note) and `itinerary_stays` (city, hotel_id, check_in_day, nights, rooms JSON, alternative_hotel_ids, estimated_cost). `itinerary_versions.generation_report` holds explanations, warnings, cost lines and totals; `vehicle_id` is on the version. The current version is the highest `version_number`; `itineraries.batch` numbers generation runs per enquiry. |
| `itinerary_restaurants` | day_id → (CASCADE), meal_type (breakfast, lunch, dinner), arrangement (hotel, restaurant, packed, own_arrangement), restaurant_id → (nullable), notes |
| `itinerary_transports` | version_id → (CASCADE), day_id →, sort_order, from_city_id →, to_city_id →, mode (coach, minibus, car, train, flight, ferry), service_type, vehicle_id → (nullable), distance_km, duration_min, is_estimate, notes |
| `itinerary_media` | version_id → (CASCADE), section (cover, day, hotel, attraction, gallery), target_id, media_id →, sort_order (PDF image overrides) |

Inventory items are always **referenced**, never copied (PRD 14.4). Free-text fields on activities let planners rename or describe without forking inventory.

## Pricing (Phase 7)

| Table | Key columns |
|---|---|
| `pricing_sheets` (1:1 version) | currency, margin_pct, discount_amount, discount_pct, manual_adjustment, rounding_rule, pax_basis, show_price_in_pdf |
| `pricing_lines` | sheet_id → (CASCADE), category (hotel, coach, transfer, sightseeing, guide, meal, other), description, basis (per_person, per_room, per_day, per_vehicle, group), unit_cost, quantity, total_cost, supplier_id →, source_type, source_id, is_estimate |

Totals are computed by the pricing engine, never stored only in the UI.

## Documents (Phase 6) ✅ migration `0007`

| Table | Key columns |
|---|---|
| `itineraries.proposal_settings` | JSON (`ProposalSettings`): template, branding, sections (order and on/off), texts (NULL = automatic), price, day photo choices, colours |
| `proposal_exports` | itinerary_id → (CASCADE), version_id → (CASCADE), version_number, file_key (unique, under `exports/`), filename (`YANA_<Tour>_<Customer>_V<n>.pdf`), template, branding, settings JSON snapshot, size_bytes, created_by_id → users |
| `app_settings['proposal_branding']` | JSON (`BrandingSettings`): company name, tagline, contact line, logo_media_id, colours, default closing, exclusions and terms, terms_reviewed |

Migration `0007`. The three templates are one HTML template with style variants (`backend/app/templates/proposal`), so they need no table.
