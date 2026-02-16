"""
API views for Smart-Travel-Planner backend.
"""
import json
import re

import requests
from django.contrib.auth import authenticate, get_user_model, login
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services.amadeus import AmadeusError, search_flights
from .models import City

User = get_user_model()


def _validate_signup_password(password: str) -> list[str]:
    """Return list of error messages for invalid password; empty list if valid."""
    errors = []
    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one number.')
    return errors


@csrf_exempt
@require_http_methods(['POST'])
def login_api(request):
    """
    Authenticate user with username and password. Returns JSON with success status and user info.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {
                'success': False,
                'message': 'Invalid JSON body. Provide username and password.',
            },
            status=400,
        )

    username = body.get('username')
    password = body.get('password')

    if not username or not password:
        return JsonResponse(
            {
                'success': False,
                'message': 'Both username and password are required.',
            },
            status=400,
        )

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse(
            {
                'success': False,
                'message': 'Invalid username or password.',
            },
            status=401,
        )

    if not user.is_active:
        return JsonResponse(
            {
                'success': False,
                'message': 'User account is disabled.',
            },
            status=403,
        )

    login(request, user)

    return JsonResponse(
        {
            'success': True,
            'message': 'Login successful.',
            'user': {
                'id': user.pk,
                'username': user.get_username(),
                'email': getattr(user, 'email', '') or '',
            },
        },
        status=200,
    )


@csrf_exempt
@require_http_methods(['POST'])
def signup_api(request):
    """
    Create a new user. Accepts full_name, email, password, confirm_password, terms_accepted.
    User can then log in with email (as username) and password.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {
                'success': False,
                'message': 'Invalid JSON body.',
            },
            status=400,
        )

    full_name = (body.get('full_name') or '').strip()
    email = (body.get('email') or '').strip().lower()
    password = body.get('password')
    confirm_password = body.get('confirm_password')
    terms_accepted = body.get('terms_accepted')

    # Required fields
    if not full_name:
        return JsonResponse(
            {'success': False, 'message': 'Full name is required.'},
            status=400,
        )
    if not email:
        return JsonResponse(
            {'success': False, 'message': 'Email address is required.'},
            status=400,
        )
    if password is None or password == '':
        return JsonResponse(
            {'success': False, 'message': 'Password is required.'},
            status=400,
        )
    if confirm_password is None:
        return JsonResponse(
            {'success': False, 'message': 'Confirm password is required.'},
            status=400,
        )

    # Email format
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse(
            {'success': False, 'message': 'Enter a valid email address.'},
            status=400,
        )

    # Password match
    if password != confirm_password:
        return JsonResponse(
            {'success': False, 'message': 'Password and confirm password do not match.'},
            status=400,
        )

    # Password strength: 8+ chars, uppercase, lowercase, number
    password_errors = _validate_signup_password(password)
    if password_errors:
        return JsonResponse(
            {
                'success': False,
                'message': ' '.join(password_errors),
            },
            status=400,
        )

    # Terms accepted
    if not terms_accepted:
        return JsonResponse(
            {
                'success': False,
                'message': 'You must agree to the Terms and Conditions and Privacy Policy.',
            },
            status=400,
        )

    # Email (username) already taken
    if User.objects.filter(username__iexact=email).exists():
        return JsonResponse(
            {'success': False, 'message': 'An account with this email already exists.'},
            status=409,
        )

    # Create user: use email as username so login with email works
    name_parts = full_name.split(None, 1)
    first_name = name_parts[0] if name_parts else full_name
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    return JsonResponse(
        {
            'success': True,
            'message': 'Account created successfully. You can now sign in.',
            'user': {
                'id': user.pk,
                'username': user.get_username(),
                'email': user.email,
                'full_name': user.get_full_name() or full_name,
            },
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(['POST'])
def flight_search_api(request):
    """
    Search for flights via Amadeus API. Accepts JSON body with:
    - departure_airport_code (or origin): 3-letter IATA code
    - destination_airport_code (or destination): 3-letter IATA code
    - travel_date: YYYY-MM-DD
    - number_of_passengers (or adults): integer 1-9

    Returns simplified list of flights. API key/secret never exposed.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON body.'},
            status=400,
        )

    origin = (
        body.get('departure_airport_code') or body.get('origin') or ''
    ).strip().upper()
    destination = (
        body.get('destination_airport_code') or body.get('destination') or ''
    ).strip().upper()
    travel_date = (
        body.get('travel_date') or body.get('departure_date') or ''
    ).strip()
    adults_raw = body.get('number_of_passengers') or body.get('adults') or body.get('passengers')
    adults = 1
    if adults_raw is not None:
        try:
            adults = int(adults_raw)
        except (TypeError, ValueError):
            adults = 1

    if not origin:
        return JsonResponse(
            {'success': False, 'message': 'Departure airport code is required.'},
            status=400,
        )
    if not destination:
        return JsonResponse(
            {'success': False, 'message': 'Destination airport code is required.'},
            status=400,
        )
    if not travel_date:
        return JsonResponse(
            {'success': False, 'message': 'Travel date is required (YYYY-MM-DD).'},
            status=400,
        )

    try:
        flights = search_flights(
            origin=origin,
            destination=destination,
            departure_date=travel_date,
            adults=adults,
        )
    except AmadeusError as e:
        status = e.status_code if e.status_code else 502
        return JsonResponse(
            {'success': False, 'message': e.message},
            status=status,
        )
    except requests.RequestException as e:
        return JsonResponse(
            {'success': False, 'message': f'Flight search service unavailable: {str(e)}'},
            status=503,
        )

    return JsonResponse(
        {
            'success': True,
            'flights': flights,
            'count': len(flights),
        },
        status=200,
    )


@require_http_methods(['GET'])
def city_search_api(request):
    """
    Search for cities/airports by name or IATA code.
    
    Query Parameters:
    - query: Search string (min 2 characters)
    - limit: Maximum results to return (default: 10, max: 50)
    
    Returns JSON with list of matching cities containing:
    - name: City name
    - iata_code: 3-letter IATA airport code
    - airport_name: Full airport name
    - country: Country name
    - country_code: 2-letter country code
    - display_name: Formatted display string
    - full_display: Full formatted display with airport and country
    """
    query = request.GET.get('query', '').strip()
    limit = request.GET.get('limit', '10')
    
    # Validate limit
    try:
        limit = int(limit)
        if limit < 1:
            limit = 10
        elif limit > 50:
            limit = 50
    except ValueError:
        limit = 10
    
    # Require at least 2 characters for search
    if len(query) < 2:
        return JsonResponse(
            {
                'success': True,
                'results': [],
                'count': 0,
                'message': 'Query must be at least 2 characters'
            },
            status=200
        )
    
    # Search by name or IATA code (case-insensitive)
    from django.db.models import Q
    
    cities = City.objects.filter(
        Q(is_active=True) &
        (Q(name__icontains=query) | 
         Q(iata_code__iexact=query) |
         Q(airport_name__icontains=query) |
         Q(country__icontains=query))
    ).order_by('name', 'iata_code')[:limit]
    
    results = []
    for city in cities:
        results.append({
            'id': city.id,
            'name': city.name,
            'iata_code': city.iata_code,
            'airport_name': city.airport_name,
            'country': city.country,
            'country_code': city.country_code,
            'display_name': city.display_name,
            'full_display': city.full_display,
        })
    
    return JsonResponse(
        {
            'success': True,
            'results': results,
            'count': len(results),
        },
        status=200
    )
