import logging
from api.models import City, ChatSession, ChatMessage
from api.services.gemini import ask_gemini
from api.services.chroma_service import chroma_client

logger = logging.getLogger(__name__)

def _platform_context_block() -> str:
    """Always-on context so the model knows what SmartTravel is and how to guide users."""
    city_samples = list(
        City.objects.filter(is_active=True).order_by('name').values_list('name', 'iata_code')[:12]
    )
    airport_line = (
        ', '.join(f"{name} ({code})" for name, code in city_samples)
        if city_samples
        else 'Airport list is seeded via admin.'
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

def fetch_context(question: str) -> str:
    """
    Searches the ChromaDB vector store for semantically similar travel data
    and formats them as a readable text context for the LLM.
    """
    context_parts = [_platform_context_block()]
    
    # Query the vector store for top 8 relevant documents
    results = chroma_client.query_documents(query=question, n_results=8)
    
    if results:
        context_parts.append("DATABASE CONTEXT (LIVE CATALOG & GUIDES):")
        for res in results:
            # We enforce a distance threshold to avoid pulling completely unrelated data
            # Cosine distance: lower is better (0.0 is perfect). < 1.5 allows broader semantic matches.
            if res['distance'] < 1.5:
                doc_text = res['document']
                # Adding the document ID in brackets so the LLM can reference it
                model_id = res['metadata'].get('model_id', '?')
                doc_type = res['metadata'].get('type', 'Item')
                context_parts.append(f"--- [{doc_type} ID: {model_id}] ---\n{doc_text}\n")
    else:
        context_parts.append("DATABASE CONTEXT: No specific listings found.")
        
    return "\n".join(context_parts)

def answer_question(question: str, session_id=None) -> dict:
    """
    Main entry point for ChatView.
    1. Fetches previous conversation history
    2. Performs semantic search in vector DB for context
    3. Calls Gemini API
    4. Saves the interaction
    """
    # 1. Session Management
    if session_id:
        try:
            session = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            session = ChatSession.objects.create(session_type='chat')
    else:
        session = ChatSession.objects.create(session_type='chat')

    # 2. Get history (last 10 messages to save context window)
    history = list(ChatMessage.objects.filter(session=session).order_by('created_at'))[-10:]

    # 3. Save User Message
    ChatMessage.objects.create(
        session=session,
        sender='user',
        content=question
    )

    # 4. Fetch Semantic Context from Vector DB
    context = fetch_context(question)

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
