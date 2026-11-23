"""Demonstration inventory (PRD Part 21).

- Countries, cities and attractions are REAL destinations (approximate coordinates).
  Opening hours and ticket prices are deliberately left empty: we do not invent them.
- Hotels, restaurants, suppliers and vehicles are FICTIONAL, named "(Demo)",
  flagged `is_demo=True`, and every price is unverified (shown as "estimated").

Load with:  python -m app.cli seed-demo   (only into an empty inventory)
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Attraction,
    City,
    Country,
    Hotel,
    HotelRoomType,
    Restaurant,
    Supplier,
    Vehicle,
    VehicleCategory,
)

# country: (name, iso, region, cities: [(name, lat, lng, nights_min, nights_max)])
COUNTRIES = [
    ("Netherlands", "NL", "Western Europe", [("Amsterdam", 52.3676, 4.9041, 2, 3), ("Rotterdam", 51.9244, 4.4777, 1, 1), ("The Hague", 52.0705, 4.3007, 1, 1)]),
    ("Belgium", "BE", "Western Europe", [("Brussels", 50.8503, 4.3517, 1, 2), ("Bruges", 51.2093, 3.2247, 1, 1), ("Ghent", 51.0543, 3.7174, 1, 1)]),
    ("France", "FR", "Western Europe", [("Paris", 48.8566, 2.3522, 3, 4), ("Lyon", 45.7640, 4.8357, 1, 2), ("Nice", 43.7102, 7.2620, 2, 3)]),
    ("Luxembourg", "LU", "Western Europe", [("Luxembourg City", 49.6116, 6.1319, 1, 1), ("Vianden", 49.9350, 6.2080, 1, 1)]),
    ("Germany", "DE", "Central Europe", [("Cologne", 50.9375, 6.9603, 1, 1), ("Heidelberg", 49.3988, 8.6724, 1, 1), ("Munich", 48.1351, 11.5820, 2, 3), ("Frankfurt", 50.1109, 8.6821, 1, 1)]),
    ("Switzerland", "CH", "Central Europe", [("Zurich", 47.3769, 8.5417, 1, 2), ("Lucerne", 47.0502, 8.3093, 2, 3), ("Interlaken", 46.6863, 7.8632, 2, 3), ("Geneva", 46.2044, 6.1432, 1, 2)]),
    ("Austria", "AT", "Central Europe", [("Vienna", 48.2082, 16.3738, 2, 3), ("Salzburg", 47.8095, 13.0550, 1, 2), ("Innsbruck", 47.2692, 11.4041, 1, 2)]),
    ("Italy", "IT", "Southern Europe", [("Rome", 41.9028, 12.4964, 3, 4), ("Florence", 43.7696, 11.2558, 2, 3), ("Venice", 45.4408, 12.3155, 1, 2), ("Milan", 45.4642, 9.1900, 1, 2)]),
]

# (city, name, category, interests, duration_min, ticket_required, child_friendly, setting, lat, lng, seasonal_info, description)
ATTRACTIONS = [
    ("Amsterdam", "Rijksmuseum", "museum", ["museums", "cultural", "historical_landmarks"], 180, True, True, "indoor", 52.3600, 4.8852, None,
     "The Netherlands' national museum, home to Dutch Golden Age masterpieces."),
    ("Amsterdam", "Canal cruise", "tour", ["scenic", "leisure", "family", "photography"], 75, True, True, "outdoor", 52.3738, 4.8910, None,
     "Boat tour through Amsterdam's UNESCO-listed canal ring."),
    ("Amsterdam", "Zaanse Schans windmills", "landmark", ["historical_landmarks", "cultural", "photography", "family"], 150, False, True, "outdoor", 52.4740, 4.8169, None,
     "Historic windmills and wooden houses north of Amsterdam; a typical half-day excursion."),
    ("Amsterdam", "Keukenhof gardens", "nature", ["nature", "photography", "scenic"], 240, True, True, "outdoor", 52.2697, 4.5465, "Spring only (typically March–May); confirm dates each year.",
     "World-famous flower gardens near Lisse."),
    ("Brussels", "Grand-Place", "landmark", ["historical_landmarks", "cultural", "photography"], 60, False, True, "outdoor", 50.8467, 4.3525, None,
     "Brussels' central square, surrounded by ornate guildhalls."),
    ("Brussels", "Atomium", "landmark", ["historical_landmarks", "family", "photography"], 90, True, True, "mixed", 50.8949, 4.3415, None,
     "Iconic structure built for the 1958 World Expo."),
    ("Bruges", "Bruges historic centre", "landmark", ["historical_landmarks", "scenic", "photography", "cultural"], 180, False, True, "outdoor", 51.2085, 3.2247, None,
     "Medieval old town with canals, belfry and market square."),
    ("Paris", "Eiffel Tower", "landmark", ["historical_landmarks", "scenic", "photography", "family"], 120, True, True, "outdoor", 48.8584, 2.2945, None,
     "Paris' most famous landmark, with viewing platforms over the city."),
    ("Paris", "Louvre Museum", "museum", ["museums", "cultural", "historical_landmarks"], 180, True, True, "indoor", 48.8606, 2.3376, None,
     "One of the world's largest art museums, home of the Mona Lisa."),
    ("Paris", "Seine river cruise", "tour", ["scenic", "leisure", "photography", "family"], 60, True, True, "outdoor", 48.8590, 2.3000, None,
     "Sightseeing cruise past Notre-Dame, the Louvre and the Eiffel Tower."),
    ("Paris", "Disneyland Paris", "theme_park", ["theme_parks", "family", "leisure"], 480, True, True, "mixed", 48.8722, 2.7758, None,
     "Disney theme parks east of Paris; a full-day family excursion."),
    ("Luxembourg City", "Bock Casemates", "landmark", ["historical_landmarks", "cultural"], 75, True, True, "mixed", 49.6117, 6.1367, None,
     "Underground defensive tunnels carved into the Bock cliff."),
    ("Vianden", "Vianden Castle", "landmark", ["historical_landmarks", "cultural", "scenic"], 90, True, True, "mixed", 49.9358, 6.2017, None,
     "Restored hilltop castle overlooking the Our valley."),
    ("Cologne", "Cologne Cathedral", "landmark", ["historical_landmarks", "cultural", "photography"], 60, False, True, "indoor", 50.9413, 6.9583, None,
     "Gothic cathedral and UNESCO World Heritage Site."),
    ("Heidelberg", "Heidelberg Castle", "landmark", ["historical_landmarks", "scenic", "photography"], 120, True, True, "mixed", 49.4106, 8.7153, None,
     "Romantic castle ruins above the Neckar river and old town."),
    ("Munich", "Marienplatz and old town", "landmark", ["historical_landmarks", "cultural", "shopping"], 90, False, True, "outdoor", 48.1374, 11.5755, None,
     "Munich's central square with the New Town Hall and Glockenspiel."),
    ("Lucerne", "Chapel Bridge", "landmark", ["historical_landmarks", "scenic", "photography"], 45, False, True, "outdoor", 47.0517, 8.3078, None,
     "Covered wooden footbridge across the Reuss, symbol of Lucerne."),
    ("Lucerne", "Mount Titlis", "mountain", ["mountains", "scenic", "adventure", "photography", "family"], 360, True, True, "outdoor", 46.7720, 8.4370, "Weather dependent; check cable car operations.",
     "Glacier mountain reached by rotating cable car from Engelberg."),
    ("Lucerne", "Lake Lucerne cruise", "lake", ["lakes", "scenic", "leisure", "photography"], 90, True, True, "outdoor", 47.0502, 8.3093, None,
     "Scenic boat trip on Lake Lucerne."),
    ("Interlaken", "Jungfraujoch", "mountain", ["mountains", "scenic", "adventure", "photography"], 480, True, True, "mixed", 46.5475, 7.9853, "Weather dependent; high altitude.",
     "High-alpine excursion by cogwheel railway to the 'Top of Europe'."),
    ("Zurich", "Zurich old town and lakefront", "landmark", ["historical_landmarks", "lakes", "shopping"], 120, False, True, "outdoor", 47.3717, 8.5423, None,
     "Walk through the Old Town, Bahnhofstrasse and along Lake Zurich."),
    ("Geneva", "Jet d'Eau and lakeside", "scenic", ["lakes", "scenic", "photography", "leisure"], 60, False, True, "outdoor", 46.2075, 6.1557, None,
     "Geneva's landmark lake fountain and promenade."),
    ("Vienna", "Schönbrunn Palace", "landmark", ["historical_landmarks", "cultural", "museums"], 180, True, True, "mixed", 48.1845, 16.3122, None,
     "Former imperial summer residence with gardens; UNESCO World Heritage Site."),
    ("Salzburg", "Salzburg old town and Mirabell Gardens", "landmark", ["historical_landmarks", "cultural", "photography"], 150, False, True, "outdoor", 47.8007, 13.0420, None,
     "Mozart's birthplace city with baroque old town and gardens."),
    ("Innsbruck", "Swarovski Crystal Worlds", "cultural", ["cultural", "shopping", "family"], 150, True, True, "mixed", 47.2944, 11.6008, None,
     "Crystal-themed attraction in Wattens, near Innsbruck."),
    ("Rome", "Colosseum", "landmark", ["historical_landmarks", "cultural", "photography"], 120, True, True, "outdoor", 41.8902, 12.4922, None,
     "Ancient Roman amphitheatre, the icon of Rome."),
    ("Rome", "Vatican Museums and Sistine Chapel", "museum", ["museums", "cultural", "historical_landmarks"], 210, True, True, "indoor", 41.9065, 12.4536, None,
     "Papal art collections and Michelangelo's Sistine Chapel ceiling."),
    ("Florence", "Uffizi Gallery", "museum", ["museums", "cultural"], 150, True, True, "indoor", 43.7678, 11.2553, None,
     "Renaissance masterpieces by Botticelli, Leonardo and Michelangelo."),
    ("Venice", "Gondola ride", "tour", ["scenic", "leisure", "photography"], 40, True, True, "outdoor", 45.4343, 12.3388, None,
     "Classic gondola ride through Venice's canals."),
    ("Milan", "Milan Cathedral (Duomo)", "landmark", ["historical_landmarks", "cultural", "shopping"], 90, True, True, "mixed", 45.4641, 9.1919, None,
     "Gothic cathedral with rooftop terraces, next to Galleria Vittorio Emanuele II."),
]

# (city, name, stars, styles, location, facilities, base prices per room type)
HOTELS = [
    ("Amsterdam", "Canal House Hotel (Demo)", 4, ["boutique"], "city_centre", ["wifi", "lift", "bar"], 210),
    ("Amsterdam", "Amstel Gateway Hotel (Demo)", 3, ["business"], "suburban", ["wifi", "restaurant", "coach_parking", "lift"], 140),
    ("Brussels", "Grand Sablon Hotel (Demo)", 4, ["business"], "city_centre", ["wifi", "restaurant", "lift"], 170),
    ("Paris", "Rive Gauche Hotel (Demo)", 4, ["boutique"], "city_centre", ["wifi", "lift", "air_conditioning"], 260),
    ("Paris", "Porte Maillot Hotel (Demo)", 3, ["business", "family"], "city_centre", ["wifi", "restaurant", "family_rooms", "lift"], 180),
    ("Paris", "Palais Étoile Hotel (Demo)", 5, ["luxury"], "city_centre", ["wifi", "spa", "restaurant", "room_service", "lift", "air_conditioning"], 520),
    ("Luxembourg City", "Kirchberg Hotel (Demo)", 4, ["business"], "suburban", ["wifi", "restaurant", "coach_parking"], 160),
    ("Heidelberg", "Neckar View Hotel (Demo)", 4, ["family"], "city_centre", ["wifi", "restaurant", "family_rooms"], 150),
    ("Munich", "Isar Park Hotel (Demo)", 4, ["business"], "city_centre", ["wifi", "restaurant", "gym", "lift"], 180),
    ("Lucerne", "Lakeside Alpine Hotel (Demo)", 4, ["family"], "city_centre", ["wifi", "restaurant", "family_rooms", "lift"], 240),
    ("Lucerne", "Pilatus Grand Hotel (Demo)", 5, ["luxury", "resort"], "resort", ["wifi", "spa", "pool", "restaurant", "room_service"], 480),
    ("Interlaken", "Jungfrau Chalet Hotel (Demo)", 3, ["family"], "city_centre", ["wifi", "restaurant", "coach_parking"], 190),
    ("Zurich", "Limmat Business Hotel (Demo)", 4, ["business"], "airport", ["wifi", "restaurant", "airport_shuttle", "gym"], 210),
    ("Vienna", "Ringstrasse Hotel (Demo)", 4, ["boutique"], "city_centre", ["wifi", "restaurant", "lift"], 170),
    ("Rome", "Via Veneto Hotel (Demo)", 4, ["boutique"], "city_centre", ["wifi", "restaurant", "air_conditioning", "lift"], 210),
    ("Venice", "Mestre Gateway Hotel (Demo)", 3, ["budget", "family"], "suburban", ["wifi", "coach_parking", "family_rooms"], 130),
]

# (city, name, cuisine, price_range, flags {veg, jain, halal, vegan, nonveg}, group_capacity)
RESTAURANTS = [
    ("Amsterdam", "Saffron Route (Demo)", "North Indian", "€€", dict(vegetarian=True, jain=True, halal=None, vegan=True, non_vegetarian=False), 80),
    ("Amsterdam", "Dam Square Brasserie (Demo)", "Continental", "€€", dict(vegetarian=True, jain=None, halal=None, vegan=None, non_vegetarian=True), 60),
    ("Brussels", "Maharaja Grand-Place (Demo)", "Indian", "€€", dict(vegetarian=True, jain=None, halal=True, vegan=None, non_vegetarian=True), 70),
    ("Paris", "Le Jardin Indien (Demo)", "Indian vegetarian", "€€", dict(vegetarian=True, jain=True, halal=None, vegan=True, non_vegetarian=False), 100),
    ("Paris", "Bistro Montmartre (Demo)", "French", "€€€", dict(vegetarian=True, jain=None, halal=None, vegan=None, non_vegetarian=True), 40),
    ("Lucerne", "Himalaya Lakeside (Demo)", "Indian", "€€€", dict(vegetarian=True, jain=None, halal=True, vegan=None, non_vegetarian=True), 90),
    ("Interlaken", "Bollywood Alps (Demo)", "Indian", "€€", dict(vegetarian=True, jain=True, halal=None, vegan=None, non_vegetarian=True), 120),
    ("Vienna", "Taj Wien (Demo)", "Indian", "€€", dict(vegetarian=True, jain=None, halal=True, vegan=None, non_vegetarian=True), 60),
    ("Rome", "Trattoria del Viaggiatore (Demo)", "Italian", "€€", dict(vegetarian=True, jain=None, halal=None, vegan=True, non_vegetarian=True), 50),
    ("Munich", "Spice Garden Munich (Demo)", "Indian", "€€", dict(vegetarian=True, jain=True, halal=None, vegan=None, non_vegetarian=True), 80),
]

SUPPLIERS = [
    ("Benelux Coach Lines (Demo)", "coach", "NL"),
    ("Alpine Transfers (Demo)", "coach", "CH"),
    ("Euro Hotel Partners (Demo)", "hotel", "FR"),
    ("Spice Route Catering (Demo)", "restaurant", "NL"),
]

# (category code, name, seats, luggage, supplier index, services, countries, price/day, price/km, driver/day)
VEHICLES = [
    ("seater_7", "Mercedes V-Class people carrier (Demo)", 7, 7, 0, ["airport_transfer", "local"], ["NL", "BE", "LU"], 450, "1.20", 0),
    ("seater_16", "16-seat Sprinter minibus (Demo)", 16, 16, 0, ["airport_transfer", "local", "intercity"], ["NL", "BE", "FR", "LU", "DE"], 650, "1.60", 180),
    ("seater_50", "50-seat touring coach (Demo)", 50, 50, 0, ["intercity", "long_distance", "local"], ["NL", "BE", "FR", "LU", "DE"], 950, "2.10", 220),
    ("luxury_coach", "36-seat VIP luxury coach (Demo)", 36, 36, 1, ["intercity", "long_distance"], ["CH", "AT", "IT", "DE"], 1300, "2.60", 240),
    ("seater_25", "25-seat midi coach (Demo)", 25, 25, 1, ["local", "intercity"], ["CH", "AT"], 800, "1.90", 200),
]


def inventory_is_empty(db: Session) -> bool:
    return (db.scalar(select(func.count()).select_from(Country)) or 0) == 0


def load_demo_inventory(db: Session) -> dict[str, int]:
    """Insert the demonstration inventory. Caller must check `inventory_is_empty` first."""
    countries: dict[str, Country] = {}
    cities: dict[str, City] = {}
    for order, (name, iso, region, city_rows) in enumerate(COUNTRIES, start=1):
        country = Country(name=name, iso_code=iso, region=region, sort_order=order)
        db.add(country)
        countries[iso] = country
        for city_name, lat, lng, n_min, n_max in city_rows:
            city = City(country=country, name=city_name, latitude=lat, longitude=lng, recommended_nights_min=n_min, recommended_nights_max=n_max)
            db.add(city)
            cities[city_name] = city
    db.flush()

    suppliers = []
    for name, kind, iso in SUPPLIERS:
        s = Supplier(name=name, supplier_type=kind, country=countries[iso], is_demo=True,
                     notes="Fictional demonstration supplier. Replace with a verified YANA partner.")
        db.add(s)
        suppliers.append(s)

    for city, name, cat, tags, dur, ticket, kids, setting, lat, lng, season, desc in ATTRACTIONS:
        db.add(Attraction(city=cities[city], name=name, category=cat, interest_tags=tags, recommended_duration_min=dur,
                          ticket_required=ticket, child_friendly=kids, setting=setting, latitude=lat, longitude=lng,
                          seasonal_info=season, description=desc, is_demo=False))

    for city, name, stars, styles, location, facilities, base in HOTELS:
        hotel = Hotel(city=cities[city], name=name, star_rating=stars, style_tags=styles, location_type=location,
                      facilities=facilities, breakfast_available=True, is_demo=True, supplier=suppliers[2],
                      description="Fictional demonstration hotel. Prices are indicative only; availability is not verified.")
        hotel.room_types = [
            HotelRoomType(name="Double / Twin", max_occupancy=2, bed_config="1 double or 2 singles", base_price=Decimal(base)),
            HotelRoomType(name="Triple", max_occupancy=3, bed_config="3 singles or double + single", base_price=Decimal(round(base * 1.35))),
            HotelRoomType(name="Family room", max_occupancy=4, bed_config="Double + 2 singles", base_price=Decimal(round(base * 1.6))),
        ]
        db.add(hotel)

    for city, name, cuisine, price_range, flags, capacity in RESTAURANTS:
        db.add(Restaurant(city=cities[city], name=name, cuisine=cuisine, price_range=price_range, group_capacity=capacity,
                          is_demo=True, supplier=suppliers[3], description="Fictional demonstration restaurant.", **flags))

    categories = {c.code: c for c in db.scalars(select(VehicleCategory))}
    for code, name, seats, luggage, sup, services, isos, per_day, per_km, driver in VEHICLES:
        db.add(Vehicle(category=categories[code], name=name, passenger_capacity=seats, luggage_capacity=luggage,
                       supplier=suppliers[sup], service_types=services, operating_countries=[countries[i] for i in isos],
                       price_per_day=Decimal(per_day), price_per_km=Decimal(per_km), driver_cost_per_day=Decimal(driver) if driver else None,
                       is_demo=True, availability_notes="Demonstration vehicle; availability not verified."))
    db.commit()
    return {
        "countries": len(COUNTRIES), "cities": len(cities), "attractions": len(ATTRACTIONS), "hotels": len(HOTELS),
        "restaurants": len(RESTAURANTS), "suppliers": len(SUPPLIERS), "vehicles": len(VEHICLES),
    }
