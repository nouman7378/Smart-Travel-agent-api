import google.generativeai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Configure the Gemini API key
api_key = getattr(settings, 'GEMINI_API_KEY', '')
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY is not set in Django settings.")

def generate_local_fallback(question: str, context: str) -> str:
    """
    Generates an intelligent travel assistant response based on matched database context,
    used when the Gemini API key is a placeholder or invalid.
    """
    question_lower = question.lower()
    
    # Parse retrieved context categories
    sections = {}
    current_section = None
    
    if context:
        for line in context.split('\n'):
            line_strip = line.strip()
            if not line_strip:
                continue
            if line_strip.endswith(':'):
                current_section = line_strip[:-1].strip()
                sections[current_section] = []
            elif line_strip.startswith('-') and current_section:
                sections[current_section].append(line_strip[1:].strip())

    resp = []
    
    # 1. Greeting
    if any(kw in question_lower for kw in ['hi', 'hello', 'hey', 'greetings', 'anyone there', 'heey']):
        resp.append("Hello! I am your SmartTravel Assistant. How can I help you plan your perfect trip today?")
        if not sections:
            resp.append("\nI can help you search for luxury hotels, find rental cars, explore budget packages, or check destination travel tips. Just ask me!")
            
    # 2. Car Rentals
    elif any(kw in question_lower for kw in ['car', 'rent', 'rental', 'vehicle', 'drive', 'cab', 'suv', 'sedan']):
        cars = sections.get('AVAILABLE RENTAL CARS', [])
        if cars:
            resp.append("Yes! We have some great rental vehicles available in our fleet:")
            resp.append("\n**Available Cars:**")
            for c in cars[:5]:
                resp.append(f"🚗 *{c}*")
            resp.append("\nAll of our rental cars include complete insurance and flexible pickup/dropoff. Let me know if you would like to secure one of these bookings!")
        else:
            resp.append("We have excellent vehicles like the Toyota Camry, BMW 3 Series, Honda Civic, and Tesla Model 3 available for rent! Let me know what location or budget you are thinking of.")

    # 3. Hotel stays & rooms
    elif any(kw in question_lower for kw in ['hotel', 'stay', 'room', 'bed', 'sleep', 'resort', 'motel', 'accommodation']):
        hotels = sections.get('AVAILABLE HOTELS', [])
        rooms = sections.get('AVAILABLE HOTEL ROOMS', [])
        
        if hotels or rooms:
            resp.append("I found some wonderful hotel and room options in our database:")
            if hotels:
                resp.append("\n**Top Matching Hotels:**")
                for h in hotels[:3]:
                    resp.append(f"🏨 *{h}*")
            if rooms:
                resp.append("\n**Available Rooms & Pricing:**")
                for r in rooms[:4]:
                    resp.append(f"🛏️ *{r}*")
            resp.append("\nWould you like me to guide you on how to book any of these or show more details?")
        else:
            resp.append("I couldn't find any active hotels or rooms matching that specific search in our catalog. Let me know if you would like me to list our top standard stays!")

    # 4. Tour Packages
    elif any(kw in question_lower for kw in ['package', 'tour', 'deal', 'trip', 'vacation', 'holiday']):
        packages = sections.get('TRAVEL PACKAGES', [])
        if packages:
            resp.append("I found some amazing complete travel packages matching your preferences:")
            for p in packages[:3]:
                resp.append(f"✈️ *{p}*")
            resp.append("\nThese packages are inclusive of return flights, hotel accommodation, and airport transfers. Let me know if you want to book one!")
        else:
            resp.append("I don't see any matching packages in that specific search, but we have amazing featured deals for Bali, Dubai, London, and the Maldives! Would you like to check one of those?")

    # 5. Destination Guide / Travel FAQ
    elif any(kw in question_lower for kw in ['guide', 'tip', 'safe', 'weather', 'attraction', 'visit', 'places', 'faqs']):
        guides = sections.get('GENERAL KNOWLEDGE BASE & DESTINATION GUIDES', [])
        if guides:
            resp.append("Here is some helpful information from our travel guides:")
            for g in guides[:2]:
                resp.append(f"\n📖 {g}")
        else:
            resp.append("I don't have a specific guide for that location in my database yet, but generally we suggest planning trips between October and April for the best weather, and utilizing ridesharing apps for secure transportation!")

    # 6. Default fallback when context has some data
    elif sections:
        resp.append("Based on what we have in our travel database, here are some options that might interest you:")
        for sec, items in sections.items():
            if items:
                resp.append(f"\n**{sec}:**")
                for item in items[:2]:
                    resp.append(f"- {item}")
        resp.append("\nHow would you like to proceed? I can help you secure a booking or customize your search!")

    # 7. Complete generic default
    else:
        resp.append("Hi! I am your AI Travel Assistant. I am ready to help you find hotels, rental cars, customized travel packages, and flight guides. Please let me know what destination or budget you are thinking of!")

    return "\n".join(resp)

def ask_gemini(question: str, context: str, history=None) -> str:
    """
    Sends context, conversation history, and user question to Gemini API using gemini-2.0-flash-exp.
    Falls back to an intelligent local RAG simulation if the Gemini API key is missing or invalid.
    """
    # Check if API key is a default placeholder
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    is_placeholder = not api_key or api_key == 'gen-lang-client-0987898960'

    if is_placeholder:
        logger.info("Placeholder GEMINI_API_KEY detected. Using local RAG fallback generator.")
        return generate_local_fallback(question, context)

    # System instruction and context setup
    system_instruction = (
        "You are an expert AI Travel Assistant for TravelHub (SmartTravel). "
        "Use the retrieved database context below to answer the user's question accurately. "
        "Be friendly, professional, concise, and helpful. If the context does not contain relevant "
        "details for the question, answer based on your general knowledge but prioritize database context. "
        "Prices are in PKR (Pakistani Rupees) unless stated otherwise."
    )

    # Format context retrieved from RAG Fetch
    context_str = f"DATABASE CONTEXT:\n{context}\n" if context else "DATABASE CONTEXT: (No matching records found in database)\n"

    # Assemble conversation history if provided (keep last 5 messages)
    history_str = ""
    if history:
        history_str = "RECENT CONVERSATION HISTORY:\n"
        for msg in history:
            role = "User" if msg.sender == 'user' else "Assistant"
            history_str += f"{role}: {msg.content}\n"
        history_str += "\n"

    # Build the final combined prompt
    prompt = (
        f"{system_instruction}\n\n"
        f"{context_str}\n"
        f"{history_str}"
        f"User: {question}\n"
        f"Assistant:"
    )

    try:
        # Use gemini-2.0-flash-exp as requested
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        return "I'm sorry, I couldn't generate a response. Please try again."
    except Exception as e:
        logger.warning(f"Error calling Gemini API: {str(e)}. Falling back to local RAG generator.")
        return generate_local_fallback(question, context)

