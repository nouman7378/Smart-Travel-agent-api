import re
from django.db.models import Q
from api.models import Hotel, Room, Car, Package, City, ChatSession, ChatMessage, KnowledgeDocument
from api.services.gemini import ask_gemini
import logging

logger = logging.getLogger(__name__)

def fetch_context(question: str) -> str:
    """
    Searches models (Hotel, Room, Car, Package, KnowledgeDocument) based on question keywords
    and formats them as a clean, readable text context for the LLM.
    """
    question_lower = question.lower()
    context_parts = []

    # 1. Location Detection
    # Get all active cities, clean their names to base names, and match against the question
    cities = list(City.objects.filter(is_active=True).values_list('name', flat=True))
    matched_locations = []
    for city_name in cities:
        # Extract base name before hyphen, dash or parenthesis
        base_name = re.split(r'[-–(]', city_name)[0].strip()
        if base_name and base_name.lower() in question_lower:
            matched_locations.append(base_name)
    # Deduplicate locations
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
        
        hotels = hotel_query[:5] # Limit to top 5 relevant hotels
        if hotels.exists():
            hotel_texts = []
            for h in hotels:
                hotel_texts.append(
                    f"- {h.name}: Located at {h.location} ({h.stars} Star, Rating: {h.rating}/5.0 based on {h.review_count} reviews). "
                    f"Distance from center: {h.distance_from_center} km. Address: {h.address}."
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
            
        rooms = room_query.select_related('hotel')[:8] # Limit to top 8 rooms
        if rooms.exists():
            room_texts = []
            for r in rooms:
                original_price_str = f" (Original Price: PKR {r.original_price:,.2f})" if r.original_price else ""
                room_texts.append(
                    f"- {r.room_type} at {r.hotel.name}: Price per night is PKR {r.price_per_night:,.2f}{original_price_str}. "
                    f"Fits up to {r.max_guests} guests. Amenities: {', '.join(r.amenities)}. "
                    f"Rooms available: {r.available_rooms}."
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

        cars = car_query[:5] # Limit to top 5 cars
        if cars.exists():
            car_texts = []
            for c in cars:
                original_price_str = f" (Original: PKR {c.original_price:,.2f})" if c.original_price else ""
                car_texts.append(
                    f"- {c.model} ({c.get_type_display()} category) by rental company '{c.company}': "
                    f"Price per day is PKR {c.price_per_day:,.2f}{original_price_str}. "
                    f"Transmission: {c.get_transmission_display()}, Seats: {c.seats}, Fuel Type: {c.get_fuel_type_display()}, "
                    f"Luggage Capacity: {c.luggage_capacity} bags. Rating: {c.rating}/5.0. Features: {', '.join(c.features)}."
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

        packages = package_query[:5] # Limit to top 5 packages
        if packages.exists():
            package_texts = []
            for p in packages:
                package_texts.append(
                    f"- {p.title} to {p.destination} ({p.nights} nights, {p.get_package_type_display()} type): "
                    f"Price per person is PKR {p.price_per_person:,.2f} (Total package: PKR {p.price_per_package:,.2f} if applicable). "
                    f"Includes hotel: {p.hotel_name} ({p.hotel_stars}★, Rating: {p.hotel_rating}). "
                    f"Includes flights on {p.airline} from {p.departure_airport} to {p.arrival_airport} (duration {p.flight_duration}). "
                    f"Highlights: {', '.join(p.highlights)}. Includes: {', '.join(p.includes)}."
                )
            context_parts.append("TRAVEL PACKAGES:\n" + "\n".join(package_texts))

    # --- KNOWLEDGE DOCUMENTS SEARCH ---
    # general FAQ/Safety/Weather tips matching destination or tags
    kd_query = KnowledgeDocument.objects.filter(is_active=True)
    if matched_locations:
        loc_queries = Q()
        for loc in matched_locations:
            loc_queries |= Q(destination__icontains=loc)
        kd_query = kd_query.filter(loc_queries)
    else:
        # If no specific location is matched, search general categories or tags matching the question
        kd_query = kd_query.filter(category='general')
        
    kds = kd_query[:3] # Limit to top 3 documents
    if kds.exists():
        kd_texts = []
        for doc in kds:
            kd_texts.append(
                f"- Travel Guide: {doc.title} (Category: {doc.get_category_display()}, Destination: {doc.destination}):\n"
                f"  Content: {doc.content}"
            )
        context_parts.append("GENERAL KNOWLEDGE BASE & DESTINATION GUIDES:\n" + "\n".join(kd_texts))

    return "\n\n".join(context_parts) if context_parts else ""

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

    # 4. Fetch last 5 messages for history memory (ordered chronologically)
    history_messages = list(session.messages.filter(
        sender__in=['user', 'assistant']
    ).order_by('-created_at')[:6]) # Fetch 6 because user message was just created.
    
    # Exclude the user message that was just created to get true history, keep max 5
    history = [m for m in history_messages if m.content != question][:5]
    history.reverse() # Order chronologically

    # 5. Call Gemini
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
