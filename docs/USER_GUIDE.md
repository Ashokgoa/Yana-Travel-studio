# User Guide

For YANA DMC administrators and travel planners. This guide grows with each phase.

## Starting the application

1. Double-click or run `scripts\start.ps1` (PowerShell). Two windows open: backend and frontend.
2. Open http://localhost:3000 in your browser.
3. On the Dashboard, **System status** should show *Operational*. If it shows *Backend unavailable*, check that the backend window is running without errors.

To stop, close both PowerShell windows (or press `Ctrl+C` in each).

## Signing in

Open http://localhost:3000 and sign in with your email and password. The first administrator is created during setup (`scripts\setup.ps1`). Administrators create everyone else under **Administration → Users**. Sessions last 12 hours; sign out with the icon next to your name (bottom left).

| Role | Can do |
|---|---|
| Administrator | Everything, including managing users |
| Travel Planner | Travel agents, customers, enquiries, dashboard |

## Dashboard

Enquiry counts by stage, recent enquiries, quick actions. Administrators also see system status.

## CRM

**Travel agents**: *CRM → Travel Agents → New travel agent*. Click an agent to see their customers and enquiries, edit details, add a customer, or start a new enquiry. *Deactivate* keeps the agent's history but blocks new customers and enquiries.

**Customers**: *CRM → Customers → New customer*. Enter adults and children; one age box appears per child. A customer can belong to a travel agent or be a direct customer.

**Enquiries**: *CRM → Enquiries → New enquiry* (or *New enquiry* from an agent or customer page, which fills in the agent and customer for you). Choose the agent, then the customer (or add one with the person-plus button). Traveller numbers are copied from the customer and can be adjusted. Each enquiry gets a reference such as **ENQ-2026-0001**.

On the enquiry page, **Change status** moves it through *New → In Progress → Proposal Generated → Sent to Agent → Revision Requested → Approved → Booking Confirmed* (or *Cancelled*). Every change is recorded in **Status history** with who, when and an optional note.

Internal notes and comments are for YANA staff only.

## Capturing customer requirements

After creating an enquiry you go straight to **Customer requirements** (also reachable from the enquiry page via *Capture requirements* / *Edit*). Nine short steps, saved each time you press **Save & continue** (or **Save draft** at any point):

1. **Travellers**: adults, children and each child's age.
2. **Travel**: arrival and departure dates (days and nights are calculated), airports, preferred start and end countries, FIT or GIT.
3. **Destinations**: add countries and, optionally, specific cities. Mark each one **Must visit** (never dropped), **Preferred**, **Optional** or **Avoid**, optionally with minimum nights. The order is your preferred route order.
4. **Interests** and travel pace.
5. **Hotels**: category, location, breakfast, and rooms (shows whether the beds fit everyone).
6. **Food**: dietary preferences and which meals to include.
7. **Transport**: vehicle types (several for mixed arrangements), seats, luggage, transfers.
8. **Budget**: per person or group total (the other is shown for reference), currency, flexibility, class.
9. **Notes**: customer requests and internal staff-only notes.

The **Readiness** panel lists anything still missing and any conflicts (for example more must-visit places than nights). The final **Review** step shows everything on one page.

## Generating itineraries

When the requirements are complete (Readiness shows *Ready for itinerary generation*), open the enquiry and click **Generate 3 alternatives**:

- **Classic**: major destinations and popular sightseeing at a balanced pace.
- **Scenic**: mountains, lakes and nature, at a more relaxed pace.
- **Premium**: higher-category hotels and transport.

Each card shows the route map, days, countries, average hotel stars and an **estimated** cost. **Compare** puts them side by side (lowest distance, price and fewest points to check are highlighted). **View day by day** shows every day with sightseeing, travel (with estimated distance and time), meals and the hotel for the night, plus:

- **Points to check**: anything you should look at, e.g. no hotel in a city, no verified restaurant for the dietary need, a long drive, over budget, a vehicle not listed for a country.
- **Why this plan**: why each city was chosen or left out.

Important: must-visit places are never dropped. If they cannot fit, the app explains why instead of generating. Prices and availability are estimates from inventory, not confirmed bookings. **Regenerate** creates a new set and keeps the old ones (see *Itinerary Builder → Saved Itineraries*). Editing an itinerary comes in the next phase.

## Editing an itinerary (Itinerary builder)

Open an itinerary and click **Edit itinerary**. Generated versions are kept unchanged, so click **Start editing** to work on a copy.

- **Days**: the pencil renames a day; **+** adds a day after it; the copy icon duplicates it; the bin removes it (not the arrival or departure day). Nights, dates, hotels and travel legs adjust automatically.
- **Activities**: drag by the handle, or use ↑/↓ (at the top or bottom of a day they move to the previous or next day). Change the time of day from the dropdown; the pencil edits the wording; the bin removes it. **Add sightseeing or free time** offers the sightseeing for that day's city from inventory (it shows if something is already on another day), plus free time or a custom activity.
- **Meals**: for each day choose *At the hotel*, a restaurant in that city (✓ means the customer's dietary need is verified there, ⚠ means it isn't), *Own arrangement*, or *Not included*.
- **Hotels**: **Replace** shows the hotels in that city with stars and a "from" price. The previous hotel is kept as an alternative.
- **Transport**: choose the vehicle for the trip and switch any leg to train.
- **Checks** (right-hand side) are re-done after every change: duplicates, closed days, too-busy days, unverified diets, meals to arrange, hotel category, vehicle size and countries, long drives, over budget. The **estimated cost** updates too.
- **Save version** gives the current state a name (e.g. "Hotel upgrades") and keeps it read-only. **Versions** lists all versions: *View* any of them, *Restore* one as a new draft (nothing is overwritten), or compare two to see what changed. **Duplicate** copies the whole itinerary.

## Pricing an itinerary (Pricing & costing)

Open an itinerary and click **Pricing**. The **Pricing & Costing** menu also lists all itineraries. This page is internal: customers never see costs, margins or profit.

- **Selling prices** at the top: per adult (twin sharing), single supplement, and child with and without a bed. If you chose another currency, it's shown underneath. The figures below them are internal: cost per adult, revenue, cost, profit and margin.
- **Cost lines** come from the itinerary and inventory: hotel rooms, vehicle and driver, tickets, restaurant meals, plus train legs and hotel meals, which have no price yet.
  - *Estimate* means an unverified inventory price; *No price* means the cost is unknown.
  - Type a new cost or quantity to override it for this proposal (*Edited*). The ↺ button goes back to inventory values. Untick a line to leave it out.
  - **Add cost line** adds guides, tolls, parking or extras. *Per person* counts once per traveller; the other bases are shared by the group.
- **Room rates**: the double and single rates per night used for the per-person prices. If a hotel has no single room, the double rate is used (*Single = double*); enter the real single rate if you know it.
- **Margins** are a percentage added on top of cost, for each category. Under each category you see its cost → selling per person.
- **Adjustments**: discount %, a fixed amount per person (+ or −), rounding up (e.g. to the nearest 10), and the child-with-bed hotel share.
- **Travellers**: taken from the enquiry. Change them here, e.g. children without a bed, or adults in single rooms (they pay the supplement).
- **Currency**: choose a second currency, type the rate (1 EUR = …) and decide what the PDF shows (EUR, the other currency, or both).
- Changes save when you leave a field. Each version has its own pricing. A new version starts with the pricing of the one it came from, and cost lines follow your edits in the builder.

**Administrators:** *Administration → Pricing defaults* sets the default margin per category, rounding, child bed share and second currency for new pricing sheets. The 15% margins are placeholders: set YANA's own, then switch on *Margins reviewed*.

## Creating the PDF proposal (PDF designer)

Open an itinerary and click **PDF proposal**, or click **PDF** in the builder. The **PDF Designer** menu also lists all itineraries.

- **Template**:
  - **Classic** is like YANA's reference brochure: route map on the first page, then the days.
  - **Premium** has a full-page photo cover and one day per page.
  - **Explorer** shows the days as a timeline with photos beside them.
- **Branding**:
  - **Travel agent** (white label): "Curated by" the agent, with the agent's contact details.
  - **YANA**: YANA's name, logo and contact details.
  - **Both**: the agent first, "in partnership with" YANA.
- **Sections**: tick or untick a section, and use the arrows to change the order.
- **Price**: the PDF shows the selling prices from **Pricing** (adult twin, single supplement, children). If the version hasn't been priced, it says *Price on request*. You can type an override price per person instead, plus a note such as "valid for June 2027". Costs and margins are never printed.
- **Text**: the title, introduction and closing message are written automatically. Edit them for this proposal, or click *Use automatic text* to go back.
- **Day photos**: per day, choose *Automatic* (first sightseeing photo, then the hotel, then the city), *No photo*, or a specific photo. Add photos in Destination Inventory first.
- **Inclusions, exclusions and terms**: inclusions come from the itinerary (hotels, meals, transport, transfers, entrance tickets); exclusions and terms come from the YANA defaults. You can edit any of them, one item per line.
- The **preview** updates as you change things. **Save settings** keeps your choices for this itinerary.
- **Create PDF** makes the A4 PDF, downloads it (for example `YANA_Classic_Europe_Sharma_Family_V2.pdf`) and lists it under *PDFs created*. If you were editing a draft, it's first saved as a read-only version named "PDF proposal", so each PDF matches a saved version. The enquiry status changes to *Proposal generated*.

**Administrators:** *Administration → Branding & PDF* holds YANA's logo (upload the official file), colours, contact line, closing message, default exclusions and terms. Replace the placeholder terms with YANA's own, then switch on *Terms reviewed*.

## Destination inventory and suppliers

Under **Destination Inventory** (Countries, Cities, Sightseeing, Hotels, Restaurants, Transportation) and **Suppliers**, everyone can search and view. **Only administrators** can add, edit, deactivate or reactivate.

- **Adding destinations needs no technical help.** Add a country, then its cities (with coordinates for routes and maps), then attractions, hotels and restaurants in those cities.
- **Yes / No / Unknown**: facts like breakfast, parking, child suitability and dietary options start as *Unknown*. Only choose *Yes* once it's confirmed with the supplier. A Jain filter shows only restaurants where Jain food is confirmed.
- **Prices** are labelled *estimated* until you tick "verified with supplier".
- **Hotels**: open a hotel to add room types (base price per room per night) and seasonal rates.
- **DEMO records** are fictional examples marked with a purple badge. Replace them with real supplier data, or deactivate them, before using them in proposals.
- **Photos**: on any country, city, sightseeing, hotel, restaurant or vehicle page, drag photos onto the *Photos* panel (or click *Add photos*). The first photo becomes the **primary** one, used in lists and proposals; click the star on another to change it. Use the arrows (or drag) to reorder, the speech-bubble to add a caption, and × to remove a photo from that record (it stays in the library). *From library* reuses an existing photo without uploading it again.
- **Image Library** (Destination Inventory → Image Library) shows every photo, where it's used, and lets administrators edit descriptions, mark images as *illustrative*, **replace** a file everywhere at once, or delete it. Location data (GPS) is removed from photos automatically.
- **Deactivate** instead of deleting: the record stays on file (and in existing itineraries) but isn't offered for new ones.
