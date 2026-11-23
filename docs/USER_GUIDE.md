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
