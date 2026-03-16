import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings

from ..models import (
    ChatMessage,
    ChatSession,
    GeneratedItinerary,
    KnowledgeDocument,
    Package,
)

try:
    # The new OpenAI SDK (>=1.x)
    from openai import APIConnectionError, APIError, OpenAI, RateLimitError
except Exception:  # pragma: no cover - library may not be installed yet
    OpenAI = None  # type: ignore
    APIError = Exception  # type: ignore
    RateLimitError = Exception  # type: ignore
    APIConnectionError = Exception  # type: ignore

logger = logging.getLogger(__name__)

_client: Optional["OpenAI"] = None


class AIServiceError(Exception):
    """Base exception for AI service problems."""


class AIConfigurationError(AIServiceError):
    """Raised when required configuration (like API key) is missing."""


def _get_openai_client() -> "OpenAI":
    """
    Lazily construct and cache the OpenAI client.
    Raises AIConfigurationError if the SDK or API key is missing.
    """
    global _client

    if _client is not None:
        return _client

    if OpenAI is None or not getattr(settings, "OPENAI_API_KEY", ""):
        raise AIConfigurationError(
            "OpenAI client is not configured. "
            "Set OPENAI_API_KEY in your backend .env file."
        )

    _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _normalise_destination_from_text(text: str) -> List[str]:
    """
    Very small heuristic destination extractor.
    For an FYP-scale system this keeps things simple while still
    letting the RAG layer focus on likely locations.
    """
    lower = text.lower()
    candidates: List[str] = []

    # Simple hard-coded destinations we explicitly support in demo data
    if "islamabad" in lower:
        candidates.append("Islamabad")
    if "murree" in lower or "muree" in lower:
        candidates.append("Murree")

    # Fallback: allow fuzzy match on known package destinations
    if not candidates:
        words = [w.strip(",.!?") for w in lower.split() if len(w) > 2]
        if words:
            qs = (
                Package.objects.filter(is_active=True)
                .filter(destination__iregex="(" + "|".join(words) + ")")
                .values_list("destination", flat=True)
                .distinct()[:5]
            )
            candidates.extend(list(qs))

    # De-duplicate while preserving order
    seen = set()
    unique: List[str] = []
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _build_rag_context(user_message: str) -> Dict[str, Any]:
    """
    Retrieve relevant structured (packages) and unstructured (knowledge documents)
    travel data from the database to ground the LLM.
    """
    destinations = _normalise_destination_from_text(user_message)

    package_qs = Package.objects.filter(is_active=True, status="active")
    doc_qs = KnowledgeDocument.objects.filter(is_active=True)

    if destinations:
        from django.db.models import Q

        dest_filter = Q()
        for dest in destinations:
            dest_filter |= Q(destination__icontains=dest)
        package_qs = package_qs.filter(dest_filter)
        doc_qs = doc_qs.filter(dest_filter)

    packages = list(
        package_qs.order_by("-is_featured", "-is_popular", "-created_at")[:5]
    )
    documents = list(doc_qs.order_by("-created_at")[:5])

    package_items = [
        {
            "id": p.id,
            "title": p.title,
            "destination": p.destination,
            "nights": p.nights,
            "price_per_person": float(p.price_per_person),
            "hotel_name": p.hotel_name,
            "highlights": p.highlights,
            "package_type": p.package_type,
        }
        for p in packages
    ]

    document_items = [
        {
            "id": d.id,
            "title": d.title,
            "destination": d.destination,
            "category": d.category,
            "content": d.content,
            "tags": d.tags,
            "source": d.source,
        }
        for d in documents
    ]

    return {
        "destinations": destinations,
        "packages": package_items,
        "knowledge_documents": document_items,
    }


def _format_rag_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Turn the structured RAG context into a compact, deterministic text
    block that can be injected into the system prompt.
    """
    lines: List[str] = []
    if context.get("destinations"):
        lines.append("Destinations inferred from user input:")
        for dest in context["destinations"]:
            lines.append(f"- {dest}")
        lines.append("")

    packages = context.get("packages") or []
    if packages:
        lines.append("Travel packages from the TravelHub database:")
        for pkg in packages:
            price = pkg.get("price_per_person")
            lines.append(
                f"- [PKG#{pkg['id']}] {pkg['title']} in {pkg['destination']} "
                f"({pkg['nights']} nights, approx PKR {price:,.0f} per person, "
                f"type={pkg['package_type']})"
            )
        lines.append("")

    documents = context.get("knowledge_documents") or []
    if documents:
        lines.append("Destination guides and travel tips:")
        for doc in documents:
            lines.append(
                f"- [DOC#{doc['id']}] {doc['title']} "
                f"(destination={doc['destination']}, category={doc['category']})"
            )
        lines.append("")

    if not lines:
        lines.append(
            "No specific database context was found. Answer using only general "
            "travel knowledge and clearly state when something is an assumption."
        )

    return "\n".join(lines)


def _base_system_prompt() -> str:
    """
    Core system instructions shared between chat and itinerary generation.
    """
    return (
        "You are TravelHub's AI Travel Assistant. You help users plan trips using "
        "trusted data from the TravelHub database.\n\n"
        "CRITICAL RULES:\n"
        "- Use ONLY the structured context and conversation history provided to you.\n"
        "- If the database context does not contain a specific fact (e.g. price, "
        "availability, visa rules), say you do not know or that the user should "
        "check official sources. Do NOT invent facts.\n"
        "- Never invent hotels, flights, or packages that are not present in the "
        "context. You may describe options generically, but concrete names must "
        "come from the context.\n"
        "- If you make assumptions, clearly label them as assumptions.\n"
        "- Keep responses concise and helpful, focusing on Pakistani travellers "
        "where relevant.\n"
    )


def generate_chat_reply(
    *,
    user,
    session: ChatSession,
    user_message: str,
    previous_messages: Sequence[ChatMessage],
) -> Dict[str, Any]:
    """
    Main entry point for the AI Chat module.
    Returns a structured payload that the view can both store and send
    directly to the frontend.
    """
    rag_context = _build_rag_context(user_message)
    rag_text = _format_rag_context_for_prompt(rag_context)

    history_messages: List[Dict[str, str]] = []
    for m in previous_messages:
        role = "assistant" if m.sender == "assistant" else "user"
        if m.sender == "system":
            role = "system"
        history_messages.append(
            {
                "role": role,
                "content": m.content[:2000],
            }
        )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _base_system_prompt()},
        {
            "role": "system",
            "content": (
                "Here is trusted database context you MUST use when answering:\n\n"
                f"{rag_text}"
            ),
        },
    ]
    messages.extend(history_messages[-10:])
    messages.append({"role": "user", "content": user_message})

    client = _get_openai_client()
    try:
        completion = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=600,
            temperature=0.3,
            timeout=getattr(settings, "OPENAI_REQUEST_TIMEOUT", 25),
        )
    except (RateLimitError, APIConnectionError, APIError) as exc:
        logger.exception("OpenAI chat completion failed")
        raise AIServiceError("Upstream AI service is temporarily unavailable.") from exc

    ai_message = (completion.choices[0].message.content or "").strip()

    # Very lightweight quick-reply suggestions (frontend can adjust text)
    quick_replies = [
        "Plan a trip",
        "Budget travel under PKR 100,000",
        "Best time to visit",
        "Family-friendly options",
    ]

    response_payload: Dict[str, Any] = {
        "message": ai_message,
        "quickReplies": quick_replies,
        "needsFollowUp": False,
        "context": {
            "destinations": rag_context.get("destinations", []),
        },
        "recommendations": {
            "type": "package",
            "items": rag_context.get("packages", []),
        },
    }

    return response_payload


def generate_itinerary(
    *,
    user,
    session: Optional[ChatSession],
    form_data: Dict[str, Any],
) -> GeneratedItinerary:
    """
    Generate a structured itinerary JSON using the LLM and RAG context.
    The returned GeneratedItinerary instance is already saved in the DB.
    """
    destination = (form_data.get("destination") or "").strip()
    start_date = (form_data.get("start_date") or "").strip()
    end_date = (form_data.get("end_date") or "").strip()
    budget = form_data.get("budget")
    preferences = (form_data.get("preferences") or "").strip()
    travelers = form_data.get("travelers") or 1

    if not destination or not start_date or not end_date:
        raise AIServiceError("Destination and travel dates are required.")

    # Reuse the same RAG context building but bias by destination
    rag_context = _build_rag_context(destination)
    rag_text = _format_rag_context_for_prompt(rag_context)

    system_prompt = (
        _base_system_prompt()
        + "\n\nYou are now generating a detailed day-by-day itinerary. "
        "Return ONLY valid JSON that matches this structure:\n"
        '{\n'
        '  "id": "string",\n'
        '  "destination": "string",\n'
        '  "startDate": "YYYY-MM-DD",\n'
        '  "endDate": "YYYY-MM-DD",\n'
        '  "budget": number,\n'
        '  "days": [\n'
        '    {\n'
        '      "day": number,\n'
        '      "date": "YYYY-MM-DD",\n'
        '      "activities": [\n'
        '        {\n'
        '          "id": "string",\n'
        '          "time": "HH:MM",\n'
        '          "title": "string",\n'
        '          "description": "string",\n'
        '          "location": "string",\n'
        '          "duration": "string",\n'
        '          "cost": number\n'
        '        }\n'
        '      ],\n'
        '      "totalCost": number\n'
        '    }\n'
        '  ],\n'
        '  "totalCost": number\n'
        '}\n'
        "If you do not know an exact price, use a reasonable estimate and make "
        "sure Day and total costs are consistent. Do NOT include any text "
        "outside the JSON."
    )

    user_instruction = (
        f"Generate a personalised itinerary for a trip.\n\n"
        f"- Destination: {destination}\n"
        f"- Start date: {start_date}\n"
        f"- End date: {end_date}\n"
        f"- Budget (approx): {budget}\n"
        f"- Number of travellers: {travelers}\n"
        f"- Preferences: {preferences or 'not specified'}\n\n"
        f"Use and reference the packages and documents from the database context "
        f"where appropriate, but do not invent new package names."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": (
                "Here is trusted database context you MUST use when designing "
                f"the itinerary:\n\n{rag_text}"
            ),
        },
        {"role": "user", "content": user_instruction},
    ]

    client = _get_openai_client()
    try:
        completion = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=900,
            temperature=0.4,
            timeout=getattr(settings, "OPENAI_REQUEST_TIMEOUT", 25),
        )
    except (RateLimitError, APIConnectionError, APIError) as exc:
        logger.exception("OpenAI itinerary completion failed")
        raise AIServiceError("Upstream AI service is temporarily unavailable.") from exc

    raw_content = (completion.choices[0].message.content or "").strip()

    try:
        itinerary_data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse itinerary JSON from model: %s", exc)
        raise AIServiceError(
            "The AI could not generate a valid itinerary format. "
            "Please try again with slightly different details."
        ) from exc

    if not isinstance(itinerary_data, dict) or "days" not in itinerary_data:
        raise AIServiceError(
            "The AI response did not contain a valid itinerary structure."
        )

    # Basic sanity checks
    itinerary_data.setdefault("destination", destination)
    itinerary_data.setdefault("startDate", start_date)
    itinerary_data.setdefault("endDate", end_date)
    if budget is not None:
        itinerary_data.setdefault("budget", budget)

    instance = GeneratedItinerary.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        session=session,
        title=f"{destination} Itinerary",
        data=itinerary_data,
    )

    return instance

