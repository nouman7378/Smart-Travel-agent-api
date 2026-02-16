"""
Amadeus Self-Service flight search integration.

Handles OAuth token retrieval and flight offers search against the Amadeus test API.
Credentials are read from Django settings (loaded from .env) and never exposed.
"""
import re
from typing import Any

import requests
from django.conf import settings

AMADEUS_TOKEN_URL = 'https://test.api.amadeus.com/v1/security/oauth2/token'
AMADEUS_FLIGHT_OFFERS_URL = 'https://test.api.amadeus.com/v2/shopping/flight-offers'

# ISO 8601 duration format: PT2H10M -> 2h 10m
DURATION_PATTERN = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')


class AmadeusError(Exception):
    """Raised when Amadeus API returns an error."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def _parse_duration(iso_duration: str) -> str:
    """
    Convert ISO 8601 duration (e.g. PT2H10M) to human-readable (e.g. 2h 10m).
    """
    if not iso_duration:
        return ''
    m = DURATION_PATTERN.match(iso_duration)
    if not m:
        return iso_duration
    hours, mins, secs = m.groups()
    parts = []
    if hours:
        parts.append(f'{int(hours)}h')
    if mins:
        parts.append(f'{int(mins)}m')
    if secs:
        parts.append(f'{int(secs)}s')
    return ' '.join(parts) or '0m'


def _get_token() -> str:
    """
    Request an OAuth access token from Amadeus test environment.
    Credentials come from settings (never exposed to frontend).
    """
    api_key = getattr(settings, 'AMADEUS_API_KEY', '') or ''
    api_secret = getattr(settings, 'AMADEUS_API_SECRET', '') or ''

    if not api_key or not api_secret:
        raise AmadeusError(
            'Amadeus API credentials are not configured. '
            'Set AMADEUS_API_KEY and AMADEUS_API_SECRET in .env.',
            status_code=500,
        )

    response = requests.post(
        AMADEUS_TOKEN_URL,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={
            'grant_type': 'client_credentials',
            'client_id': api_key,
            'client_secret': api_secret,
        },
        timeout=15,
    )

    if response.status_code != 200:
        try:
            body = response.json()
            msg = body.get('error_description', body.get('error', response.text))
        except Exception:
            msg = response.text
        raise AmadeusError(
            f'Amadeus authentication failed: {msg}',
            status_code=response.status_code,
            details=response.text,
        )

    data = response.json()
    token = data.get('access_token')
    if not token:
        raise AmadeusError('Amadeus token response missing access_token', status_code=500)
    return token


def search_flights(
    *,
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
) -> list[dict[str, Any]]:
    """
    Search for flight offers via Amadeus test environment.

    Args:
        origin: Departure airport IATA code (e.g. JFK, LHR)
        destination: Destination airport IATA code
        departure_date: Date in YYYY-MM-DD format
        adults: Number of adult passengers (1–9)

    Returns:
        List of simplified flight objects suitable for frontend consumption.
        Each flight includes: airline_name, flight_number, departure_time,
        arrival_time, duration, stops, price.
    """
    origin = (origin or '').strip().upper()
    destination = (destination or '').strip().upper()
    departure_date = (departure_date or '').strip()

    if not origin or len(origin) != 3:
        raise AmadeusError('Invalid departure airport code. Use a 3-letter IATA code.')
    if not destination or len(destination) != 3:
        raise AmadeusError('Invalid destination airport code. Use a 3-letter IATA code.')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', departure_date):
        raise AmadeusError('Invalid travel date. Use YYYY-MM-DD format.')
    if not isinstance(adults, int) or adults < 1 or adults > 9:
        raise AmadeusError('Number of passengers must be between 1 and 9.')

    token = _get_token()

    response = requests.get(
        AMADEUS_FLIGHT_OFFERS_URL,
        headers={'Authorization': f'Bearer {token}'},
        params={
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': adults,
        },
        timeout=20,
    )

    if response.status_code == 401:
        # Token might be expired; could retry with new token
        raise AmadeusError('Amadeus authentication expired. Please try again.', status_code=401)
    if response.status_code != 200:
        try:
            body = response.json()
            errors = body.get('errors', [])
            msg = errors[0].get('detail', str(errors)) if errors else response.text
        except Exception:
            msg = response.text
        raise AmadeusError(
            f'Amadeus flight search failed: {msg}',
            status_code=response.status_code,
            details=response.text,
        )

    data = response.json()
    offers = data.get('data') or []
    dictionaries = data.get('dictionaries') or {}
    carriers = dictionaries.get('carriers') or {}

    results = []
    for offer in offers:
        itineraries = offer.get('itineraries') or []
        price_info = offer.get('price') or {}
        total_price = price_info.get('total') or price_info.get('grandTotal') or '0'
        currency = price_info.get('currency') or 'USD'

        # Build first itinerary (outbound) summary
        first_itinerary = itineraries[0] if itineraries else {}
        segments = first_itinerary.get('segments') or []
        num_stops = max(0, len(segments) - 1)

        # Use first segment for primary flight info (or combine if multi-leg)
        primary_segment = segments[0] if segments else {}
        carrier_code = primary_segment.get('carrierCode') or ''
        flight_num = primary_segment.get('number') or ''
        airline_name = carriers.get(carrier_code, carrier_code) if carrier_code else 'Unknown'

        dep = primary_segment.get('departure') or {}
        arr = segments[-1].get('arrival') if segments else {}
        departure_at = dep.get('at', '')
        arrival_at = arr.get('at', '')

        # Format times for frontend (keep ISO if needed, or HH:MM)
        def _format_time(iso_str: str) -> str:
            if not iso_str:
                return ''
            try:
                # "2024-01-15T10:30:00" -> "10:30"
                return iso_str[11:16] if len(iso_str) >= 16 else iso_str
            except Exception:
                return iso_str

        duration_raw = first_itinerary.get('duration') or ''
        duration_display = _parse_duration(duration_raw)

        results.append({
            'airline_name': airline_name,
            'flight_number': f'{carrier_code}{flight_num}' if carrier_code or flight_num else '',
            'departure_time': _format_time(departure_at),
            'departure_datetime': departure_at,
            'arrival_time': _format_time(arrival_at),
            'arrival_datetime': arrival_at,
            'duration': duration_display,
            'duration_raw': duration_raw,
            'stops': num_stops,
            'price': total_price,
            'currency': currency,
        })

    return results
