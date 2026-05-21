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

def _is_casual_smalltalk(question_lower: str) -> bool:
    """True when the message is general chat, not a catalog lookup."""
    casual_phrases = (
        'how are you', 'how r u', "what's up", 'whats up', 'good morning',
        'good evening', 'good night', 'thank you', 'thanks', 'thx',
        'bye', 'goodbye', 'see you', 'lol', 'haha', 'nice', 'cool',
        'who are you', 'what can you do', 'help me', 'bored', 'joke',
    )
    if any(p in question_lower for p in casual_phrases):
        return True
    # Short greetings only
    stripped = question_lower.strip('!?., ')
    if stripped in ('hi', 'hey', 'hello', 'yo', 'sup', 'heey', 'hiya'):
        return True
    return False


def _casual_smalltalk_reply(question_lower: str) -> str | None:
    """Friendly replies that do not require database context."""
    if any(w in question_lower for w in ('thank', 'thx', 'appreciate')):
        return (
            "You're very welcome! 😊 If anything else comes up for your trip — "
            "hotels, flights, cars, packages — just ping me."
        )
    if any(w in question_lower for w in ('bye', 'goodbye', 'see you', 'good night')):
        return "Take care! Safe travels whenever you head out. ✈️"
    if 'how are you' in question_lower or 'how r u' in question_lower:
        return (
            "I'm doing great, thanks for asking! 😄 "
            "What about you — got a trip in mind, or just browsing ideas?"
        )
    if any(w in question_lower for w in ("what's up", 'whats up', 'sup', 'yo')):
        return "Not much — just here to help you plan something fun. Where's your head at, travel-wise?"
    if any(w in question_lower for w in ('who are you', 'what can you do', 'what do you do')):
        return (
            "I'm your SmartTravel buddy — think friendly travel agent in chat form. "
            "I can chat about trips, suggest ideas, and pull real listings from our site "
            "(hotels, cars, packages) when we've got them. No pressure — what's on your mind?"
        )
    if 'joke' in question_lower:
        return (
            "Why did the passport blush? It saw the traveler's strip search at security. 😅 "
            "Okay, I'm better at trip planning than stand-up — where would you actually like to go?"
        )
    if any(w in question_lower for w in ('hi', 'hello', 'hey', 'greetings', 'heey', 'hiya')):
        return (
            "Hey! 👋 Good to see you. I'm here for whatever — trip planning, random travel questions, "
            "or just figuring out where to go next. What's up?"
        )
    return None


def generate_local_fallback(question: str, context: str) -> str:
    """
    Generates an intelligent travel assistant response based on matched database context,
    used when the Gemini API key is a placeholder or invalid.
    """
    question_lower = question.lower().strip()
    
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

    # Casual chat — always respond warmly, even with zero DB context
    if _is_casual_smalltalk(question_lower):
        smalltalk = _casual_smalltalk_reply(question_lower)
        if smalltalk:
            return smalltalk

    resp = []
    
    # 1. Greeting (broader patterns)
    if any(kw in question_lower for kw in ['hi', 'hello', 'hey', 'greetings', 'anyone there', 'heey']):
        resp.append("Hey! 👋 I'm your SmartTravel assistant — happy to help you plan a trip or just chat travel.")
        if not sections:
            resp.append(
                "\nTell me a vibe (beach, city, mountains?) or a budget, and we'll figure something out — "
                "or browse Hotels / Packages on the site whenever you're ready."
            )
            
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
            resp.append(
                "I don't have an exact match in our catalog for that right now — listings change as admins add them. "
                "No worries though: try the Hotels page, or tell me a city + budget (e.g. \"Islamabad under 15k\") "
                "and I'll search again when we've got data. Want general tips on picking a stay meanwhile?"
            )

    # 4. Tour Packages
    elif any(kw in question_lower for kw in ['package', 'tour', 'deal', 'trip', 'vacation', 'holiday']):
        packages = sections.get('TRAVEL PACKAGES', [])
        if packages:
            resp.append("I found some amazing complete travel packages matching your preferences:")
            for p in packages[:3]:
                resp.append(f"✈️ *{p}*")
            resp.append("\nThese packages are inclusive of return flights, hotel accommodation, and airport transfers. Let me know if you want to book one!")
        else:
            resp.append(
                "Nothing in our package catalog matches that search at the moment — still happy to brainstorm! "
                "Packages on the site get updated regularly. What destination and rough budget are you thinking? "
                "(Weekend getaway vs full week makes a big difference.)"
            )

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

    # 7. Empty DB context — stay conversational, don't go blank
    elif not sections and not context.strip():
        if any(kw in question_lower for kw in ['hotel', 'stay', 'room', 'car', 'rent', 'package', 'flight', 'trip', 'travel', 'vacation']):
            resp.append(
                "Good question! I checked our live catalog and didn't pull up specific listings for that yet — "
                "the database might be empty for that search, or we need a bit more detail."
            )
            resp.append(
                "\nTry: a city name, your budget in PKR, and dates (even rough). "
                "Or hop to Flights / Hotels / Packages in the menu — I'll sound smarter once listings are in. "
                "Want to tell me where you're hoping to go?"
            )
        else:
            resp.append(
                "I'm here! 😊 Not everything needs a database answer — ask me travel stuff, say hi, "
                "or tell me what kind of trip you're dreaming about (beach, city break, family, budget?)."
            )

    # 8. Complete generic default
    else:
        resp.append(
            "Got it! I'm your travel sidekick on SmartTravel — hotels, cars, packages, flights, random tips. "
            "What's the plan, or should we start with where you'd like to go?"
        )

    return "\n".join(resp)


def _build_system_instruction(has_db_context: bool) -> str:
    """System persona: warm and human; uses DB when available, never goes silent without it."""
    base = (
        "You are the SmartTravel (TravelHub) AI travel buddy — warm, casual, and human, "
        "like a helpful friend at a travel desk, not a corporate FAQ bot.\n\n"
        "WHAT YOU KNOW:\n"
        "- SmartTravel is a travel site: hotels/rooms, flights, car hire, packages, deals, community, cart + Stripe checkout.\n"
        "- PLATFORM CONTEXT in the prompt describes site sections and sample airports — use it to guide users to the right page.\n"
        "- RECENT CONVERSATION HISTORY is the ongoing chat — refer back to what the user already said (budget, city, dates).\n"
        "- DATABASE CONTEXT has live catalog rows when relevant; CATALOG SNAPSHOT / teasers summarize what else exists on the site.\n\n"
        "STYLE:\n"
        "- Use natural, conversational language. Short paragraphs are fine.\n"
        "- Light emoji occasionally (e.g. one per message max), never spam them.\n"
        "- Match the user's tone: casual if they're casual, a bit more structured if they're planning.\n"
        "- Ask at most 1–2 friendly follow-up questions when useful (destination, budget in PKR, dates, travelers).\n"
        "- For greetings, thanks, jokes, or off-topic chat: respond naturally first; gently tie back to travel only if it fits.\n"
        "- When listing options from context, use bullet points or short numbered lists — easy to scan.\n\n"
        "DATABASE / RAG RULES:\n"
        "- When DATABASE CONTEXT lists real hotels, rooms, cars, or packages: quote them accurately (names, PKR prices, IDs if shown).\n"
        "- NEVER invent specific listing names, prices, or availability that are not in the context.\n"
    )
    if has_db_context:
        base += (
            "- Prioritize the database context for booking-related answers.\n"
        )
    else:
        base += (
            "- DATABASE CONTEXT is empty or has no matching records. This is normal — do NOT reply with only "
            "\"no data\", a blank answer, or refuse to chat.\n"
            "- Still have a full, friendly conversation: general travel advice, destination ideas, packing tips, "
            "visa basics (high-level only), best seasons, etc.\n"
            "- For our catalog (hotels/cars/packages on this site): say you're not seeing exact matches in the "
            "catalog right now, suggest they browse the site sections, and offer to help once they share city + budget.\n"
            "- You may suggest popular destination types (beach, city, mountains) without claiming they're in our DB.\n"
        )
    base += "\nPrices on this platform are in PKR unless stated otherwise."
    return base


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

    ctx = (context or "").strip()
    has_listings = bool(
        ctx
        and any(
            marker in ctx
            for marker in (
                'AVAILABLE HOTELS',
                'AVAILABLE HOTEL ROOMS',
                'AVAILABLE RENTAL CARS',
                'TRAVEL PACKAGES',
                'TRAVEL GUIDES & TIPS',
                'GENERAL KNOWLEDGE BASE',
            )
        )
    )
    has_db_context = has_listings
    system_instruction = _build_system_instruction(has_db_context)

    if has_listings:
        context_str = f"DATABASE CONTEXT (use for listings):\n{ctx}\n"
    elif ctx:
        context_str = f"{ctx}\n"
    else:
        context_str = (
            "DATABASE CONTEXT: (empty — no catalog rows matched this message; "
            "still reply in a warm, human way using general travel knowledge.)\n"
        )

    history_str = ""
    if history:
        history_str = "RECENT CONVERSATION HISTORY (continue this thread naturally):\n"
        for msg in history:
            role = "User" if msg.sender == 'user' else "Assistant"
            # Trim very long prior turns so the model keeps room for catalog context
            content = msg.content if len(msg.content) <= 500 else msg.content[:500] + "…"
            history_str += f"{role}: {content}\n"
        history_str += "\n"

    try:
        model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            system_instruction=system_instruction,
        )
        # User turn only in the prompt; system instruction sets persona
        user_prompt = (
            f"{context_str}\n"
            f"{history_str}"
            f"User: {question}\n"
            f"Assistant:"
        )
        response = model.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.85,
                max_output_tokens=1024,
            ),
        )
        if response and response.text:
            text = response.text.strip()
            if text:
                return text
        return generate_local_fallback(question, context)
    except Exception as e:
        logger.warning(f"Error calling Gemini API: {str(e)}. Falling back to local RAG generator.")
        return generate_local_fallback(question, context)

