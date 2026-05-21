import re
from django.db.models import Q
from api.models import Hotel, Room, Car, Package, City, ChatSession, ChatMessage, KnowledgeDocument
from api.services.gemini import ask_gemini
import logging

logger = logging.getLogger(__name__)

# Stopwords for loose keyword search across catalog text fields
_SEARCH_STOPWORDS = frozenset({
    'what', 'when', 'where', 'which', 'would', 'could', 'should', 'about', 'there',
    'their', 'these', 'those', 'please', 'thanks', 'thank', 'hello', 'help',
    'want', 'need', 'like', 'best', 'good', 'cheap', 'travel', 'trip', 'going',
})


def _platform_context_block() -> str:
    """Always-on context so the model knows what SmartTravel is and how to guide users."""
    city_samples = list(
        City.objects.filter(is_active=True).order_by('name').values_list('name', 'iata_code')[:12]
    )
    airport_line = (
        ', '.join(f"{name} ({code})" for name, code in city_samples)
        if city_samples
        else 'Airport list is seeded via admin (IATA autocomplete on Flights page).'
    )

    return (
        "PLATFORM CONTEXT (SmartTravel / TravelHub):\n"
        "- Travel booking website: hotels & rooms, flight search, car rentals, vacation packages, deals, and a travel community feed.\n"
        "- All catalog prices are in PKR (Pakistani Rupees).\n"
        "- Users sign up / log in, add items to a booking cart, and can pay via Stripe at checkout.\n"
        "- Main pages: Hotels (/hotels), Flights (/flights), Cars (/cars), Packages (/packages), Deals (/deals), "
        "Community (/community), Profile & bookings after login.\n"
        "- Flight search uses real-time APIs with airport/city autocomplete; hotel/car/package listings come from the admin catalog below.\n"
        "- This chat can quote live catalog data when provided in DATABASE CONTEXT — never invent listing IDs or prices.\n"
        f"- Sample airports/cities in our system: {airport_line}.\n"
        "- Pakistan-focused content and resources exist on the site; users may also ask about international destinations in general terms.\n"
    )


def _question_keywords(question_lower: str) -> list[str]:
    """Significant tokens from the user message for fuzzy catalog/knowledge search."""
    tokens = re.findall(r'[a-z0-9]{3,}', question_lower)
    return [t for t in tokens if t not in _SEARCH_STOPWORDS][:8]


def fetch_context(question: str) -> str:
    """
    Searches models (Hotel, Room, Car, Package, KnowledgeDocument) based on question keywords
    and formats them as a clean, readable text context for the LLM.
    """
    question_lower = question.lower().strip()
    context_parts = [_platform_context_block()]
    keywords = _question_keywords(question_lower)

    # 1. Location Detection
    # Get all active cities, clean their names to base names, and match against the question
    cities = list(City.objects.filter(is_active=True).values_list('name', flat=True))
    matched_locations = []
    for city_name in cities:
        # Extract base name before hyphen, dash or parenthesis
        base_name = re.split(r'[-–(]', city_name)[0].strip()
        if base_name and base_name.lower() in question_lower:
            matched_locations.append(base_name)
    # Match IATA codes mentioned in the question (e.g. "ISB to DXB")
    for _name, iata in City.objects.filter(is_active=True).values_list('name', 'iata_code'):
        if iata and len(iata) == 3 and re.search(rf'\b{re.escape(iata.lower())}\b', question_lower):
            base = re.split(r'[-–(]', _name)[0].strip() or _name
            matched_locations.append(base)
    matched_locations = list(set(matched_locations))
    
    # 2. Extract potential price/budget limits using regex (e.g., "under 5000", "below 10000", "budget 8000")
    budget_limit = None
    price_match = re.search(r'(?:under|below|budget|less than|max|maximum)\s*(?:pkr)?\s*(\d+[\d,.]*)', question_lower)
    if price_match:
        try:
            budget_limit = float(price_match.group(1).replace(',', ''))
        except ValueError:
            pass

    # --- HOTEL SEARCH ---
    # Triggered if question mentions hotels or stays, or matches a specific location
    has_hotel_keywords = any(kw in question_lower for kw in ['hotel', 'stay', 'resort', 'motel', 'hostel', 'lodging', 'accommodation'])
    if has_hotel_keywords or matched_locations:
        hotel_query = Hotel.objects.filter(is_active=True)
        if matched_locations:
            # Match hotels by location
            loc_queries = Q()
            for loc in matched_locations:
                loc_queries |= Q(location__icontains=loc) | Q(address__icontains=loc)
            hotel_query = hotel_query.filter(loc_queries)
        
        if keywords and not matched_locations:
            kw_q = Q()
            for kw in keywords:
                kw_q |= Q(name__icontains=kw) | Q(location__icontains=kw) | Q(address__icontains=kw)
            hotel_query = hotel_query.filter(kw_q)

        hotels = hotel_query[:6]
        if hotels.exists():
            hotel_texts = []
            for h in hotels:
                hotel_texts.append(
                    f"- [Hotel ID {h.pk}] {h.name}: {h.location} ({h.stars}★, {h.rating}/5 from {h.review_count} reviews). "
                    f"{h.distance_from_center} km from center. Address: {h.address}. "
                    f"Book via Hotels page → hotel detail."
                )
            context_parts.append("AVAILABLE HOTELS:\n" + "\n".join(hotel_texts))

    # --- ROOM SEARCH ---
    # Triggered if question mentions rooms, beds, nights, suites or price filters
    has_room_keywords = any(kw in question_lower for kw in ['room', 'suite', 'bed', 'sleep', 'guest', 'night', 'price', 'cost', 'pkr', 'budget'])
    if has_room_keywords or budget_limit:
        room_query = Room.objects.filter(is_active=True)
        
        # Apply location filter if matched
        if matched_locations:
            loc_queries = Q()
            for loc in matched_locations:
                loc_queries |= Q(hotel__location__icontains=loc)
            room_query = room_query.filter(loc_queries)
            
        # Apply budget filter if extracted
        if budget_limit:
            room_query = room_query.filter(price_per_night__lte=budget_limit)
            
        if keywords and not matched_locations and not budget_limit:
            kw_q = Q()
            for kw in keywords:
                kw_q |= Q(room_type__icontains=kw) | Q(hotel__name__icontains=kw) | Q(hotel__location__icontains=kw)
            room_query = room_query.filter(kw_q)

        rooms = room_query.select_related('hotel')[:8]
        if rooms.exists():
            room_texts = []
            for r in rooms:
                original_price_str = f" (was PKR {r.original_price:,.0f})" if r.original_price else ""
                amenities = ', '.join(r.amenities) if r.amenities else 'standard amenities'
                room_texts.append(
                    f"- [Room ID {r.pk}] {r.room_type} at {r.hotel.name} ({r.hotel.location}): "
                    f"PKR {r.price_per_night:,.0f}/night{original_price_str}. "
                    f"Up to {r.max_guests} guests, {r.available_rooms} left. Amenities: {amenities}."
                )
            context_parts.append("AVAILABLE HOTEL ROOMS:\n" + "\n".join(room_texts))

    # --- CAR SEARCH ---
    # Triggered if question mentions cars, rental, driving, etc.
    has_car_keywords = any(kw in question_lower for kw in ['car', 'rent', 'rental', 'vehicle', 'drive', 'suv', 'sedan', 'cab'])
    if has_car_keywords:
        car_query = Car.objects.filter(is_available=True)
        
        # Filter by car type if mentioned
        for choice_key, choice_val in Car.CAR_TYPES:
            if choice_key in question_lower or choice_val.lower() in question_lower:
                car_query = car_query.filter(type=choice_key)
                
        # Filter by budget if extracted
        if budget_limit:
            car_query = car_query.filter(price_per_day__lte=budget_limit)

        if keywords:
            kw_q = Q()
            for kw in keywords:
                kw_q |= Q(model__icontains=kw) | Q(company__icontains=kw) | Q(type__icontains=kw)
            car_query = car_query.filter(kw_q)

        cars = car_query[:6]
        if cars.exists():
            car_texts = []
            for c in cars:
                original_price_str = f" (was PKR {c.original_price:,.0f})" if c.original_price else ""
                features = ', '.join(c.features) if c.features else 'standard features'
                rating_str = f"{c.rating}/5" if c.rating else "no rating yet"
                car_texts.append(
                    f"- [Car ID {c.pk}] {c.model} ({c.get_type_display()}) from {c.company}: "
                    f"PKR {c.price_per_day:,.0f}/day{original_price_str}. "
                    f"{c.get_transmission_display()}, {c.seats} seats, {c.get_fuel_type_display()}, "
                    f"{c.luggage_capacity} bags, mileage: {c.mileage}. Rating: {rating_str}. Features: {features}."
                )
            context_parts.append("AVAILABLE RENTAL CARS:\n" + "\n".join(car_texts))

    # --- PACKAGE SEARCH ---
    # Triggered if question mentions packages, trip, vacation, cultural, beach, packages, deals
    has_package_keywords = any(kw in question_lower for kw in ['package', 'deal', 'tour', 'trip', 'vacation', 'holiday'])
    if has_package_keywords or matched_locations:
        package_query = Package.objects.filter(is_active=True)
        
        if matched_locations:
            loc_queries = Q()
            for loc in matched_locations:
                loc_queries |= Q(destination__icontains=loc)
            package_query = package_query.filter(loc_queries)
            
        if budget_limit:
            package_query = package_query.filter(price_per_person__lte=budget_limit)

        if keywords and not matched_locations:
            kw_q = Q()
            for kw in keywords:
                kw_q |= (
                    Q(title__icontains=kw)
                    | Q(destination__icontains=kw)
                    | Q(hotel_name__icontains=kw)
                    | Q(package_type__icontains=kw)
                )
            package_query = package_query.filter(kw_q)

        packages = package_query[:6]
        if packages.exists():
            package_texts = []
            for p in packages:
                highlights = ', '.join(p.highlights) if p.highlights else 'see package page'
                includes = ', '.join(p.includes) if p.includes else 'flights + hotel bundle'
                total_str = (
                    f", total from PKR {p.price_per_package:,.0f}"
                    if p.price_per_package
                    else ""
                )
                package_texts.append(
                    f"- [Package ID {p.pk}] {p.title} → {p.destination} ({p.nights} nights, "
                    f"{p.get_package_type_display()}): PKR {p.price_per_person:,.0f}/person{total_str}. "
                    f"Hotel: {p.hotel_name} ({p.hotel_stars}★, {p.hotel_rating}/5). "
                    f"Flight: {p.airline}, {p.departure_airport}→{p.arrival_airport}, {p.flight_duration}, "
                    f"{p.flight_stops} stop(s), dep {p.departure_time} arr {p.arrival_time}. "
                    f"Slots left: {p.remaining_availability}. Highlights: {highlights}. Includes: {includes}."
                )
            context_parts.append("TRAVEL PACKAGES:\n" + "\n".join(package_texts))

    # --- KNOWLEDGE DOCUMENTS SEARCH ---
    kd_query = KnowledgeDocument.objects.filter(is_active=True)
    if matched_locations:
        loc_queries = Q()
        for loc in matched_locations:
            loc_queries |= Q(destination__icontains=loc)
        kd_query = kd_query.filter(loc_queries)
    elif keywords:
        kw_q = Q()
        for kw in keywords:
            kw_q |= Q(title__icontains=kw) | Q(content__icontains=kw) | Q(destination__icontains=kw)
        kd_query = kd_query.filter(kw_q | Q(category='general'))
    else:
        kd_query = kd_query.filter(category='general')

    kds = kd_query[:4]
    if kds.exists():
        kd_texts = []
        for doc in kds:
            content_preview = doc.content[:600] + ('…' if len(doc.content) > 600 else '')
            kd_texts.append(
                f"- [{doc.get_category_display()}] {doc.title}"
                f"{f' ({doc.destination})' if doc.destination else ''}:\n"
                f"  {content_preview}"
            )
        context_parts.append("TRAVEL GUIDES & TIPS (knowledge base):\n" + "\n".join(kd_texts))

    # Listing sections beyond platform block
    if len(context_parts) > 1:
        teaser = _catalog_teaser_block()
        if teaser:
            context_parts.append(teaser)
        return "\n\n".join(context_parts)

    context_parts.append(_catalog_snapshot_for_empty_context())
    return "\n\n".join(context_parts)


def _catalog_teaser_block() -> str:
    """Brief cross-catalog hints so the model can mention other options on the site."""
    lines = ["OTHER INVENTORY ON SITE (quick reference):"]
    for h in Hotel.objects.filter(is_active=True).order_by('-rating')[:3]:
        lines.append(f"- Hotel: {h.name} in {h.location} ({h.stars}★, PKR rooms on detail page)")
    for c in Car.objects.filter(is_available=True).order_by('price_per_day')[:2]:
        lines.append(f"- Car: {c.model} from {c.company} (~PKR {c.price_per_day:,.0f}/day)")
    for p in Package.objects.filter(is_active=True).order_by('-is_featured', '-is_popular')[:2]:
        lines.append(f"- Package: {p.title} → {p.destination} (from PKR {p.price_per_person:,.0f}/person)")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _catalog_snapshot_for_empty_context() -> str:
    """Richer summary when RAG found no rows; avoids blank or robotic 'no data' replies."""
    hotel_n = Hotel.objects.filter(is_active=True).count()
    room_n = Room.objects.filter(is_active=True).count()
    car_n = Car.objects.filter(is_available=True).count()
    pkg_n = Package.objects.filter(is_active=True).count()
    kd_n = KnowledgeDocument.objects.filter(is_active=True).count()

    if hotel_n + room_n + car_n + pkg_n + kd_n == 0:
        return (
            "CATALOG SNAPSHOT: The live catalog is currently empty (no hotels, rooms, cars, "
            "packages, or guides seeded yet). Still chat warmly — general travel advice is fine; "
            "do not invent specific listings."
        )

    parts = [
        "CATALOG SNAPSHOT (no exact match for this message — site still has inventory):",
        f"- Counts: {hotel_n} hotels, {room_n} room types, {car_n} rental cars, {pkg_n} packages, {kd_n} travel guides.",
        "Ask the user for: destination/city, budget in PKR, dates, and travelers to narrow search.",
    ]

    sample_hotels = list(
        Hotel.objects.filter(is_active=True).order_by('-rating').values_list('name', 'location', 'stars')[:4]
    )
    if sample_hotels:
        parts.append(
            "- Top hotels: "
            + "; ".join(f"{n} in {loc} ({s}★)" for n, loc, s in sample_hotels)
        )

    sample_rooms = Room.objects.filter(is_active=True).select_related('hotel').order_by('price_per_night')[:3]
    if sample_rooms:
        parts.append(
            "- Cheapest rooms: "
            + "; ".join(
                f"{r.room_type} @ {r.hotel.name} PKR {r.price_per_night:,.0f}/night"
                for r in sample_rooms
            )
        )

    sample_cars = Car.objects.filter(is_available=True).order_by('price_per_day')[:3]
    if sample_cars:
        parts.append(
            "- Cars from: "
            + "; ".join(f"{c.model} ({c.company}) PKR {c.price_per_day:,.0f}/day" for c in sample_cars)
        )

    sample_pkgs = Package.objects.filter(is_active=True).order_by('-is_featured')[:3]
    if sample_pkgs:
        parts.append(
            "- Packages: "
            + "; ".join(
                f"{p.title} → {p.destination} (PKR {p.price_per_person:,.0f}/person, {p.nights} nights)"
                for p in sample_pkgs
            )
        )

    destinations = list(
        Package.objects.filter(is_active=True)
        .values_list('destination', flat=True)
        .distinct()[:6]
    )
    if destinations:
        parts.append(f"- Package destinations available: {', '.join(destinations)}.")

    return "\n".join(parts)


def answer_question(question: str, session_id=None) -> dict:
    """
    Core RAG workflow:
    1. Retrieve or create a ChatSession
    2. Save the user's question to ChatMessage
    3. Retrieve context matching the question keywords from DB
    4. Keep the last 5 messages from ChatSession for memory history
    5. Query Gemini with the combined prompt
    6. Save Gemini's answer to ChatMessage
    7. Return the response dict with answer and session_id
    """
    # 1. Retrieve or create session
    session = None
    if session_id:
        try:
            session = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            pass
            
    if not session:
        session = ChatSession.objects.create(
            session_type='chat',
            title=question[:50] + "..." if len(question) > 50 else question
        )

    # 2. Save User Message
    ChatMessage.objects.create(
        session=session,
        sender='user',
        content=question
    )

    # 3. Retrieve Context from Database
    context = fetch_context(question)

    # 4. Fetch last 8 messages for history memory (ordered chronologically)
    history_messages = list(
        session.messages.filter(sender__in=['user', 'assistant']).order_by('-created_at')[:10]
    )

    history = [m for m in history_messages if m.content != question][:8]
    history.reverse()

    # 5. Call Gemini (platform + RAG context + conversation memory)
    answer = ask_gemini(question, context, history)

    # 6. Save Assistant Response
    ChatMessage.objects.create(
        session=session,
        sender='assistant',
        content=answer
    )

    # Update session's last activity
    session.save()

    return {
        "answer": answer,
        "session_id": session.pk
    }
