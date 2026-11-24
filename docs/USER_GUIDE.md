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
