"""
API views for Smart-Travel-Planner backend.
"""
import json
import re

import requests
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    Car,
    ChatMessage,
    ChatSession,
    City,
    GeneratedItinerary,
    Hotel,
    Package,
    Room,
)
from .services.ai import (
    AIConfigurationError,
    AIServiceError,
    generate_chat_reply,
    generate_itinerary,
)
from .services.amadeus import AmadeusError, search_flights

User = get_user_model()


def is_superadmin(user):
    """Check if user is a super admin."""
    return user.is_authenticated and user.is_staff


def check_admin_auth(request):
    """
    Check if the request is from an authenticated admin user.
    Tries session auth first, then falls back to basic auth for API testing.
    """
    # First check session authentication
    if request.user.is_authenticated and request.user.is_staff:
        return True, request.user
    
    # For development: check basic auth header as fallback
    import base64
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Basic '):
        try:
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)
            user = authenticate(request, username=username, password=password)
            if user and user.is_authenticated and user.is_staff:
                return True, user
        except Exception:
            pass
    
    return False, None

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


@require_http_methods(['GET'])
def admin_user_list_api(request):
    """
    List users for the admin dashboard (Super Admin only).
    
    Returns a simplified list of users with fields needed by the React admin UI.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403,
        )

    users_qs = User.objects.all().order_by('-date_joined')

    results = []
    for u in users_qs:
        results.append(
            {
                'id': str(u.pk),
                'email': getattr(u, 'email', '') or '',
                'name': u.get_full_name() or u.get_username() or (u.email or ''),
                # Map Django flags to our simple role model
                'role': 'admin' if u.is_staff else 'traveler',
                'status': 'active' if u.is_active else 'inactive',
                'registrationDate': u.date_joined.isoformat() if getattr(u, 'date_joined', None) else '',
                'lastLogin': u.last_login.isoformat() if getattr(u, 'last_login', None) else '',
                # Placeholder booking/spend stats until booking model exists
                'totalBookings': 0,
                'totalSpent': 0,
                'phone': getattr(u, 'phone', '') if hasattr(u, 'phone') else '',
            }
        )

    return JsonResponse(
        {
            'success': True,
            'users': results,
            'count': len(results),
        },
        status=200,
    )


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
                'is_staff': user.is_staff,
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


# ==================== HOTEL MANAGEMENT API ====================

@require_http_methods(['GET'])
def hotel_list_api(request):
    """
    Get list of active hotels for users.
    Supports filtering by location and search query.
    """
    location = request.GET.get('location', '').strip()
    search = request.GET.get('search', '').strip()
    min_stars = request.GET.get('min_stars', '')
    
    # Base queryset - only active hotels
    hotels = Hotel.objects.filter(is_active=True)
    
    # Filter by location
    if location:
        hotels = hotels.filter(location__icontains=location)
    
    # Search by name or location
    if search:
        from django.db.models import Q
        hotels = hotels.filter(
            Q(name__icontains=search) | 
            Q(location__icontains=search) |
            Q(address__icontains=search)
        )
    
    # Filter by minimum stars
    if min_stars:
        try:
            min_stars = int(min_stars)
            hotels = hotels.filter(stars__gte=min_stars)
        except ValueError:
            pass
    
    # Order by rating (highest first)
    hotels = hotels.order_by('-rating', '-created_at')
    
    results = []
    for hotel in hotels:
        results.append({
            'id': hotel.id,
            'name': hotel.name,
            'location': hotel.location,
            'address': hotel.address,
            'stars': hotel.stars,
            'rating': float(hotel.rating),
            'review_count': hotel.review_count,
            'distance_from_center': float(hotel.distance_from_center),
            'image_url': hotel.image_url,
            'display_distance': hotel.display_distance,
        })
    
    return JsonResponse(
        {
            'success': True,
            'hotels': results,
            'count': len(results),
        },
        status=200
    )


@require_http_methods(['GET'])
def hotel_detail_api(request, hotel_id):
    """
    Get detailed information about a specific hotel.
    """
    try:
        hotel = Hotel.objects.get(id=hotel_id, is_active=True)
        
        return JsonResponse(
            {
                'success': True,
                'hotel': {
                    'id': hotel.id,
                    'name': hotel.name,
                    'location': hotel.location,
                    'address': hotel.address,
                    'stars': hotel.stars,
                    'rating': float(hotel.rating),
                    'review_count': hotel.review_count,
                    'distance_from_center': float(hotel.distance_from_center),
                    'image_url': hotel.image_url,
                    'display_distance': hotel.display_distance,
                    'created_at': hotel.created_at.isoformat(),
                    'updated_at': hotel.updated_at.isoformat(),
                },
            },
            status=200
        )
    except Hotel.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Hotel not found.'},
            status=404
        )


@csrf_exempt
@require_http_methods(['POST'])
def hotel_create_api(request):
    """
    Create a new hotel (Super Admin only).
    Supports image upload to Cloudinary.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        # Handle multipart form data for file upload
        name = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        address = request.POST.get('address', '').strip()
        stars = request.POST.get('stars', '3')
        rating = request.POST.get('rating', '0')
        review_count = request.POST.get('review_count', '0')
        distance_from_center = request.POST.get('distance_from_center', '0')
        
        # Validation
        if not name:
            return JsonResponse(
                {'success': False, 'message': 'Hotel name is required.'},
                status=400
            )
        if not location:
            return JsonResponse(
                {'success': False, 'message': 'Location is required.'},
                status=400
            )
        if not address:
            return JsonResponse(
                {'success': False, 'message': 'Address is required.'},
                status=400
            )
        
        # Convert numeric fields
        try:
            stars = int(stars)
            if stars < 1 or stars > 5:
                stars = 3
        except ValueError:
            stars = 3
        
        try:
            rating = float(rating)
            if rating < 0 or rating > 5:
                rating = 0
        except ValueError:
            rating = 0
        
        try:
            review_count = int(review_count)
            if review_count < 0:
                review_count = 0
        except ValueError:
            review_count = 0
        
        try:
            distance_from_center = float(distance_from_center)
            if distance_from_center < 0:
                distance_from_center = 0
        except ValueError:
            distance_from_center = 0
        
        # Handle image upload to Cloudinary
        image_url = ''
        upload_error = None
        if 'image' in request.FILES:
            try:
                # Import cloudinary here to ensure config is loaded
                import cloudinary.uploader
                # Debug info
                print(f"Uploading image: {request.FILES['image'].name}, size: {request.FILES['image'].size}", file=sys.stderr)
                upload_result = cloudinary.uploader.upload(
                    request.FILES['image'],
                    folder='hotels/',
                    resource_type='image'
                )
                image_url = upload_result.get('secure_url', '')
                print(f"Upload successful: {image_url}", file=sys.stderr)
            except Exception as e:
                # Log the error but don't fail - create hotel without image
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Cloudinary upload failed: {str(e)}')
                print(f'Cloudinary upload error: {str(e)}', file=sys.stderr)
                upload_error = str(e)
                # Continue without image - hotel will be created without an image URL
        
        # Create hotel
        hotel = Hotel.objects.create(
            name=name,
            location=location,
            address=address,
            stars=stars,
            rating=rating,
            review_count=review_count,
            distance_from_center=distance_from_center,
            image_url=image_url,
            is_active=True
        )
        
        # Build response message
        message = 'Hotel created successfully.'
        if upload_error:
            message += f' (Image upload failed: {upload_error})'
        
        return JsonResponse(
            {
                'success': True,
                'message': message,
                'hotel': {
                    'id': hotel.id,
                    'name': hotel.name,
                    'location': hotel.location,
                    'address': hotel.address,
                    'stars': hotel.stars,
                    'rating': float(hotel.rating),
                    'review_count': hotel.review_count,
                    'distance_from_center': float(hotel.distance_from_center),
                    'image_url': hotel.image_url,
                },
            },
            status=201
        )
        
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error creating hotel: {str(e)}'},
            status=500
        )


@csrf_exempt
@require_http_methods(['POST'])
def hotel_update_api(request, hotel_id):
    """
    Update an existing hotel (Super Admin only).
    Supports image upload to Cloudinary.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        hotel = Hotel.objects.get(id=hotel_id)
    except Hotel.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Hotel not found.'},
            status=404
        )
    
    try:
        # Handle multipart form data for file upload
        name = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        address = request.POST.get('address', '').strip()
        stars = request.POST.get('stars', str(hotel.stars))
        rating = request.POST.get('rating', str(hotel.rating))
        review_count = request.POST.get('review_count', str(hotel.review_count))
        distance_from_center = request.POST.get('distance_from_center', str(hotel.distance_from_center))
        is_active = request.POST.get('is_active')
        
        # Update fields if provided
        if name:
            hotel.name = name
        if location:
            hotel.location = location
        if address:
            hotel.address = address
        
        # Convert numeric fields
        try:
            stars = int(stars)
            if 1 <= stars <= 5:
                hotel.stars = stars
        except ValueError:
            pass
        
        try:
            rating = float(rating)
            if 0 <= rating <= 5:
                hotel.rating = rating
        except ValueError:
            pass
        
        try:
            review_count = int(review_count)
            if review_count >= 0:
                hotel.review_count = review_count
        except ValueError:
            pass
        
        try:
            distance_from_center = float(distance_from_center)
            if distance_from_center >= 0:
                hotel.distance_from_center = distance_from_center
        except ValueError:
            pass
        
        if is_active is not None:
            hotel.is_active = is_active.lower() in ('true', '1', 'yes')
        
        # Handle image upload to Cloudinary
        if 'image' in request.FILES:
            try:
                # Import cloudinary here to ensure config is loaded
                import cloudinary.uploader
                upload_result = cloudinary.uploader.upload(
                    request.FILES['image'],
                    folder='hotels/',
                    resource_type='image'
                )
                hotel.image_url = upload_result.get('secure_url', '')
            except Exception as e:
                # Log the error but don't fail - update hotel without new image
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Cloudinary upload failed: {str(e)}')
                # Continue without updating image
        
        hotel.save()
        
        return JsonResponse(
            {
                'success': True,
                'message': 'Hotel updated successfully.',
                'hotel': {
                    'id': hotel.id,
                    'name': hotel.name,
                    'location': hotel.location,
                    'address': hotel.address,
                    'stars': hotel.stars,
                    'rating': float(hotel.rating),
                    'review_count': hotel.review_count,
                    'distance_from_center': float(hotel.distance_from_center),
                    'image_url': hotel.image_url,
                    'is_active': hotel.is_active,
                },
            },
            status=200
        )
        
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error updating hotel: {str(e)}'},
            status=500
        )


@csrf_exempt
@require_http_methods(['POST'])
def hotel_delete_api(request, hotel_id):
    """
    Delete a hotel (Super Admin only).
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        hotel = Hotel.objects.get(id=hotel_id)
        hotel_name = hotel.name
        hotel.delete()
        
        return JsonResponse(
            {
                'success': True,
                'message': f'Hotel "{hotel_name}" deleted successfully.',
            },
            status=200
        )
    except Hotel.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Hotel not found.'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error deleting hotel: {str(e)}'},
            status=500
        )


@require_http_methods(['GET'])
def hotel_rooms_api(request, hotel_id):
    """
    Get all rooms for a specific hotel (user-facing endpoint).
    Only returns active rooms with available inventory.
    """
    try:
        hotel = Hotel.objects.get(id=hotel_id, is_active=True)
        rooms = Room.objects.filter(hotel=hotel, is_active=True, available_rooms__gt=0)
        
        results = []
        for room in rooms:
            results.append({
                'id': room.id,
                'room_type': room.room_type,
                'description': room.description,
                'price_per_night': float(room.price_per_night),
                'original_price': float(room.original_price) if room.original_price else None,
                'available_rooms': room.available_rooms,
                'max_guests': room.max_guests,
                'room_image_url': room.room_image_url,
                'amenities': room.amenities,
                'discount_percentage': room.discount_percentage,
            })
        
        return JsonResponse(
            {
                'success': True,
                'hotel': {
                    'id': hotel.id,
                    'name': hotel.name,
                    'location': hotel.location,
                },
                'rooms': results,
                'count': len(results),
            },
            status=200
        )
        
    except Hotel.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Hotel not found or inactive.'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error fetching rooms: {str(e)}'},
            status=500
        )


@csrf_exempt
@require_http_methods(['POST'])
def room_create_api(request, hotel_id):
    """
    Create a new room for a hotel (Super Admin only).
    Supports image upload to Cloudinary.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        hotel = Hotel.objects.get(id=hotel_id)
        
        # Handle image upload to Cloudinary
        room_image_url = ''
        upload_error = None
        if 'image' in request.FILES:
            try:
                # Import cloudinary here to ensure config is loaded
                import cloudinary.uploader
                # Debug info
                print(f"Uploading room image: {request.FILES['image'].name}, size: {request.FILES['image'].size}", file=sys.stderr)
                upload_result = cloudinary.uploader.upload(
                    request.FILES['image'],
                    folder='rooms/',
                    resource_type='image'
                )
                room_image_url = upload_result.get('secure_url', '')
                print(f"Room image upload successful: {room_image_url}", file=sys.stderr)
            except Exception as e:
                # Log the error but don't fail - create room without image
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Cloudinary room image upload failed: {str(e)}')
                print(f'Cloudinary room image upload error: {str(e)}', file=sys.stderr)
                upload_error = str(e)
                # Continue without image - room will be created without an image URL
        
        # Parse form data
        room_type = request.POST.get('room_type', '')
        description = request.POST.get('description', '')
        price_per_night = request.POST.get('price_per_night', '')
        original_price = request.POST.get('original_price', '')
        available_rooms = request.POST.get('available_rooms', '')
        max_guests = request.POST.get('max_guests', '2')
        amenities_json = request.POST.get('amenities', '[]')
        is_active = request.POST.get('is_active', 'True')
        
        # Validate required fields
        if not room_type:
            return JsonResponse(
                {'success': False, 'message': 'room_type is required.'},
                status=400
            )
        
        if not price_per_night:
            return JsonResponse(
                {'success': False, 'message': 'price_per_night is required.'},
                status=400
            )
        
        if not available_rooms:
            return JsonResponse(
                {'success': False, 'message': 'available_rooms is required.'},
                status=400
            )
        
        # Parse amenities
        try:
            amenities = json.loads(amenities_json)
        except json.JSONDecodeError:
            amenities = []
        
        # Create room
        room = Room.objects.create(
            hotel=hotel,
            room_type=room_type,
            description=description,
            price_per_night=price_per_night,
            original_price=original_price if original_price else None,
            available_rooms=available_rooms,
            max_guests=max_guests,
            room_image_url=room_image_url,
            amenities=amenities,
            is_active=is_active.lower() == 'true'
        )
        
        return JsonResponse(
            {
                'success': True,
                'message': f'Room "{room.room_type}" created successfully.',
                'room': {
                    'id': room.id,
                    'room_type': room.room_type,
                    'price_per_night': float(room.price_per_night),
                    'available_rooms': room.available_rooms,
                }
            },
            status=201
        )
        
    except Hotel.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Hotel not found.'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error creating room: {str(e)}'},
            status=500
        )


@csrf_exempt
@require_http_methods(['PUT'])
def room_update_api(request, room_id):
    """
    Update a room (Super Admin only).
    Supports image upload to Cloudinary.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        room = Room.objects.get(id=room_id)
        
        # Handle image upload to Cloudinary
        if 'image' in request.FILES:
            try:
                # Import cloudinary here to ensure config is loaded
                import cloudinary.uploader
                # Debug info
                print(f"Updating room image: {request.FILES['image'].name}, size: {request.FILES['image'].size}", file=sys.stderr)
                upload_result = cloudinary.uploader.upload(
                    request.FILES['image'],
                    folder='rooms/',
                    resource_type='image'
                )
                room.room_image_url = upload_result.get('secure_url', '')
                print(f"Room image update successful: {room.room_image_url}", file=sys.stderr)
            except Exception as e:
                # Log the error but don't fail - continue with other updates
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Cloudinary room image update failed: {str(e)}')
                print(f'Cloudinary room image update error: {str(e)}', file=sys.stderr)
                # Continue without updating image
        
        # Parse form data (for non-file fields)
        # Note: For PUT requests with FormData, we need to handle it differently
        # In practice, you might want to use PATCH instead of PUT for partial updates
        
        # Update fields if provided in request.POST
        if 'room_type' in request.POST:
            room.room_type = request.POST['room_type']
        if 'description' in request.POST:
            room.description = request.POST['description']
        if 'price_per_night' in request.POST:
            room.price_per_night = request.POST['price_per_night']
        if 'original_price' in request.POST:
            room.original_price = request.POST['original_price'] if request.POST['original_price'] else None
        if 'available_rooms' in request.POST:
            room.available_rooms = request.POST['available_rooms']
        if 'max_guests' in request.POST:
            room.max_guests = request.POST['max_guests']
        if 'amenities' in request.POST:
            try:
                room.amenities = json.loads(request.POST['amenities'])
            except json.JSONDecodeError:
                pass  # Keep existing amenities
        if 'is_active' in request.POST:
            room.is_active = request.POST['is_active'].lower() == 'true'
        
        room.save()
        
        return JsonResponse(
            {
                'success': True,
                'message': f'Room "{room.room_type}" updated successfully.',
                'room': {
                    'id': room.id,
                    'room_type': room.room_type,
                    'price_per_night': float(room.price_per_night),
                    'available_rooms': room.available_rooms,
                    'is_active': room.is_active,
                }
            },
            status=200
        )
        
    except Room.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Room not found.'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error updating room: {str(e)}'},
            status=500
        )


@csrf_exempt
@require_http_methods(['DELETE'])
def room_delete_api(request, room_id):
    """
    Delete a room (Super Admin only).
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        room = Room.objects.get(id=room_id)
        room_type = room.room_type
        room.delete()
        
        return JsonResponse(
            {
                'success': True,
                'message': f'Room "{room_type}" deleted successfully.',
            },
            status=200
        )
    except Room.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Room not found.'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error deleting room: {str(e)}'},
            status=500
        )


@require_http_methods(['GET'])
def room_admin_list_api(request, hotel_id):
    """
    Get all rooms for a hotel (Super Admin only).
    Includes both active and inactive rooms.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        hotel = Hotel.objects.get(id=hotel_id)
        rooms = Room.objects.filter(hotel=hotel).order_by('price_per_night')
        
        results = []
        for room in rooms:
            results.append({
                'id': room.id,
                'room_type': room.room_type,
                'description': room.description,
                'price_per_night': float(room.price_per_night),
                'original_price': float(room.original_price) if room.original_price else None,
                'available_rooms': room.available_rooms,
                'max_guests': room.max_guests,
                'room_image_url': room.room_image_url,
                'amenities': room.amenities,
                'is_active': room.is_active,
                'discount_percentage': room.discount_percentage,
                'created_at': room.created_at.isoformat(),
                'updated_at': room.updated_at.isoformat(),
            })
        
        return JsonResponse(
            {
                'success': True,
                'hotel': {
                    'id': hotel.id,
                    'name': hotel.name,
                },
                'rooms': results,
                'count': len(results),
            },
            status=200
        )
        
    except Hotel.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Hotel not found.'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error fetching rooms: {str(e)}'},
            status=500
        )

@require_http_methods(['GET'])
def hotel_admin_list_api(request):
    """
    Get all hotels for admin management (Super Admin only).
    Includes both active and inactive hotels.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    hotels = Hotel.objects.all().order_by('-created_at')
    
    results = []
    for hotel in hotels:
        results.append({
            'id': hotel.id,
            'name': hotel.name,
            'location': hotel.location,
            'address': hotel.address,
            'stars': hotel.stars,
            'rating': float(hotel.rating),
            'review_count': hotel.review_count,
            'distance_from_center': float(hotel.distance_from_center),
            'image_url': hotel.image_url,
            'is_active': hotel.is_active,
            'created_at': hotel.created_at.isoformat(),
            'updated_at': hotel.updated_at.isoformat(),
        })
    
    return JsonResponse(
        {
            'success': True,
            'hotels': results,
            'count': len(results),
        },
        status=200
    )


# === Car API Endpoints ===


@csrf_exempt
@require_http_methods(['GET'])
def car_list_api(request):
    """List all available cars with filtering options."""
    try:
        # Get query parameters
        car_type = request.GET.get('type')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        company = request.GET.get('company')
        
        # Base query - only available cars
        cars = Car.objects.filter(is_available=True)
        
        # Apply filters
        if car_type:
            cars = cars.filter(type=car_type)
        
        if company:
            cars = cars.filter(company=company)
        
        if min_price:
            cars = cars.filter(price_per_day__gte=min_price)
        
        if max_price:
            cars = cars.filter(price_per_day__lte=max_price)
        
        # Sorting options
        sort_by = request.GET.get('sort_by', 'price')
        if sort_by == 'price_high':
            cars = cars.order_by('-price_per_day')
        elif sort_by == 'rating':
            cars = cars.order_by('-rating')
        else:
            cars = cars.order_by('price_per_day')
        
        # Prepare results
        results = []
        for car in cars:
            results.append({
                'id': car.id,
                'model': car.model,
                'type': car.type,
                'type_display': car.get_type_display(),
                'company': car.company,
                'price_per_day': float(car.price_per_day),
                'original_price': float(car.original_price) if car.original_price else None,
                'discount_percentage': car.discount_percentage,
                'car_image_url': car.car_image_url,
                'transmission': car.transmission,
                'seats': car.seats,
                'luggage_capacity': car.luggage_capacity,
                'fuel_type': car.fuel_type,
                'mileage': car.mileage,
                'rating': float(car.rating) if car.rating else None,
                'review_count': car.review_count,
                'features': car.features,
                'created_at': car.created_at.isoformat(),
                'updated_at': car.updated_at.isoformat(),
            })
        
        return JsonResponse(
            {
                'success': True,
                'cars': results,
                'count': len(results),
            },
            status=200
        )
    
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)},
            status=400
        )


@csrf_exempt
@require_http_methods(['GET'])
def car_admin_list_api(request):
    """
    Get all cars for admin management (Super Admin only).
    Includes both available and unavailable cars.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    cars = Car.objects.all().order_by('-created_at')
    
    results = []
    for car in cars:
        results.append({
            'id': car.id,
            'model': car.model,
            'type': car.type,
            'type_display': car.get_type_display(),
            'company': car.company,
            'price_per_day': float(car.price_per_day),
            'original_price': float(car.original_price) if car.original_price else None,
            'discount_percentage': car.discount_percentage,
            'car_image_url': car.car_image_url,
            'transmission': car.transmission,
            'seats': car.seats,
            'luggage_capacity': car.luggage_capacity,
            'fuel_type': car.fuel_type,
            'mileage': car.mileage,
            'rating': float(car.rating) if car.rating else None,
            'review_count': car.review_count,
            'features': car.features,
            'is_available': car.is_available,
            'created_at': car.created_at.isoformat(),
            'updated_at': car.updated_at.isoformat(),
        })
    
    return JsonResponse(
        {
            'success': True,
            'cars': results,
            'count': len(results),
        },
        status=200
    )


@csrf_exempt
@require_http_methods(['GET'])
def car_detail_api(request, car_id):
    """Get specific car details by ID."""
    try:
        car = Car.objects.get(id=car_id, is_available=True)
        
        car_data = {
            'id': car.id,
            'model': car.model,
            'type': car.type,
            'type_display': car.get_type_display(),
            'company': car.company,
            'price_per_day': float(car.price_per_day),
            'original_price': float(car.original_price) if car.original_price else None,
            'discount_percentage': car.discount_percentage,
            'car_image_url': car.car_image_url,
            'transmission': car.transmission,
            'transmission_display': car.get_transmission_display(),
            'seats': car.seats,
            'luggage_capacity': car.luggage_capacity,
            'fuel_type': car.fuel_type,
            'fuel_type_display': car.get_fuel_type_display(),
            'mileage': car.mileage,
            'rating': float(car.rating) if car.rating else None,
            'review_count': car.review_count,
            'features': car.features,
            'is_available': car.is_available,
            'created_at': car.created_at.isoformat(),
            'updated_at': car.updated_at.isoformat(),
        }
        
        return JsonResponse(
            {
                'success': True,
                'car': car_data,
            },
            status=200
        )
        
    except Car.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Car not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)},
            status=400
        )


@csrf_exempt
@require_http_methods(['POST'])
def car_create_api(request):
    """Create a new car (admin only). Supports JSON and multipart form data."""
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )

    try:
        # If the request is coming from an HTML form (multipart/form-data),
        # read fields from request.POST instead of assuming raw JSON.
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            model = request.POST.get('model', '').strip()
            company = request.POST.get('company', '').strip()
            car_type = request.POST.get('type', '').strip()
            price_per_day = request.POST.get('price_per_day', '').strip()
            original_price = request.POST.get('original_price', '').strip()
            transmission = request.POST.get('transmission', '').strip() or 'automatic'
            seats = request.POST.get('seats', '').strip()
            luggage_capacity = request.POST.get('luggage_capacity', '').strip() or '2'
            fuel_type = request.POST.get('fuel_type', '').strip() or 'gasoline'
            mileage = request.POST.get('mileage', '').strip() or 'Unlimited'
            rating = request.POST.get('rating', '').strip()
            review_count = request.POST.get('review_count', '').strip() or '0'
            features_raw = request.POST.get('features', '').strip()
            is_available_raw = request.POST.get('is_available', 'true').strip().lower()

            # Basic required-field validation
            missing_fields = []
            if not model:
                missing_fields.append('model')
            if not company:
                missing_fields.append('company')
            if not car_type:
                missing_fields.append('type')
            if not price_per_day:
                missing_fields.append('price_per_day')
            if not transmission:
                missing_fields.append('transmission')
            if not seats:
                missing_fields.append('seats')

            if missing_fields:
                return JsonResponse(
                    {
                        'success': False,
                        'message': f"Missing required fields: {', '.join(missing_fields)}",
                    },
                    status=400,
                )

            # Validate choices
            valid_types = [choice[0] for choice in Car.CAR_TYPES]
            if car_type not in valid_types:
                return JsonResponse(
                    {
                        'success': False,
                        'message': f'Invalid car type. Valid types: {", ".join(valid_types)}',
                    },
                    status=400,
                )

            valid_transmissions = [choice[0] for choice in Car.TRANSMISSION_TYPES]
            if transmission not in valid_transmissions:
                return JsonResponse(
                    {
                        'success': False,
                        'message': f'Invalid transmission. Valid types: {", ".join(valid_transmissions)}',
                    },
                    status=400,
                )

            valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
            if fuel_type not in valid_fuel_types:
                return JsonResponse(
                    {
                        'success': False,
                        'message': f'Invalid fuel type. Valid types: {", ".join(valid_fuel_types)}',
                    },
                    status=400,
                )

            # Parse features (either JSON array or comma-separated string)
            features = []
            if features_raw:
                try:
                    parsed = json.loads(features_raw)
                    if isinstance(parsed, list):
                        features = parsed
                except json.JSONDecodeError:
                    features = [item.strip() for item in features_raw.split(',') if item.strip()]

            # Boolean conversion
            is_available = is_available_raw in ('true', '1', 'yes', 'on')

            # Optional image URL coming from the form (we ignore uploaded file here)
            car_image_url = request.POST.get('car_image_url', '').strip()

            car = Car.objects.create(
                model=model,
                type=car_type,
                company=company,
                price_per_day=price_per_day,
                original_price=original_price or None,
                car_image_url=car_image_url,
                transmission=transmission,
                seats=seats,
                luggage_capacity=luggage_capacity,
                fuel_type=fuel_type,
                mileage=mileage,
                rating=rating or None,
                review_count=review_count,
                features=features,
                is_available=is_available,
            )

        else:
            # Original JSON-based API (e.g., Postman / programmatic clients)
            data = json.loads(request.body.decode('utf-8'))

            # Required fields
            required_fields = ['model', 'type', 'company', 'price_per_day', 'transmission', 'seats']
            for field in required_fields:
                if field not in data:
                    return JsonResponse(
                        {'success': False, 'message': f'{field} is required'},
                        status=400
                    )

            # Validate car type
            valid_types = [choice[0] for choice in Car.CAR_TYPES]
            if data['type'] not in valid_types:
                return JsonResponse(
                    {'success': False, 'message': f'Invalid car type. Valid types: {", ".join(valid_types)}'},
                    status=400
                )

            # Validate transmission
            valid_transmissions = [choice[0] for choice in Car.TRANSMISSION_TYPES]
            if data['transmission'] not in valid_transmissions:
                return JsonResponse(
                    {'success': False, 'message': f'Invalid transmission. Valid types: {", ".join(valid_transmissions)}'},
                    status=400
                )

            # Validate fuel type if provided
            if 'fuel_type' in data:
                valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
                if data['fuel_type'] not in valid_fuel_types:
                    return JsonResponse(
                        {'success': False, 'message': f'Invalid fuel type. Valid types: {", ".join(valid_fuel_types)}'},
                        status=400
                    )

            car = Car.objects.create(
                model=data['model'],
                type=data['type'],
                company=data['company'],
                price_per_day=data['price_per_day'],
                original_price=data.get('original_price'),
                car_image_url=data.get('car_image_url', ''),
                transmission=data['transmission'],
                seats=data['seats'],
                luggage_capacity=data.get('luggage_capacity', 2),
                fuel_type=data.get('fuel_type', 'gasoline'),
                mileage=data.get('mileage', 'Unlimited'),
                rating=data.get('rating'),
                review_count=data.get('review_count', 0),
                features=data.get('features', []),
                is_available=data.get('is_available', True),
            )

        return JsonResponse(
            {
                'success': True,
                'message': 'Car created successfully',
                'car_id': car.id,
            },
            status=201
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON data'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)},
            status=400
        )


@csrf_exempt
@require_http_methods(['POST'])
def car_update_api(request, car_id):
    """Update an existing car (admin only). Supports JSON and multipart form data."""
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )

    try:
        car = Car.objects.get(id=car_id)

        if request.content_type and request.content_type.startswith('multipart/form-data'):
            # Read updates from form data
            if 'model' in request.POST:
                car.model = request.POST.get('model', car.model).strip()
            if 'company' in request.POST:
                car.company = request.POST.get('company', car.company).strip()
            if 'type' in request.POST:
                car_type = request.POST.get('type', car.type).strip()
                valid_types = [choice[0] for choice in Car.CAR_TYPES]
                if car_type in valid_types:
                    car.type = car_type
                else:
                    return JsonResponse(
                        {
                            'success': False,
                            'message': f'Invalid car type. Valid types: {", ".join(valid_types)}',
                        },
                        status=400,
                    )
            if 'price_per_day' in request.POST:
                car.price_per_day = request.POST.get('price_per_day', car.price_per_day)
            if 'original_price' in request.POST:
                original_price = request.POST.get('original_price', '')
                car.original_price = original_price or None
            if 'transmission' in request.POST:
                transmission = request.POST.get('transmission', car.transmission).strip()
                valid_transmissions = [choice[0] for choice in Car.TRANSMISSION_TYPES]
                if transmission in valid_transmissions:
                    car.transmission = transmission
                else:
                    return JsonResponse(
                        {
                            'success': False,
                            'message': f'Invalid transmission. Valid types: {", ".join(valid_transmissions)}',
                        },
                        status=400,
                    )
            if 'seats' in request.POST:
                car.seats = request.POST.get('seats', car.seats)
            if 'luggage_capacity' in request.POST:
                car.luggage_capacity = request.POST.get('luggage_capacity', car.luggage_capacity)
            if 'fuel_type' in request.POST:
                fuel_type = request.POST.get('fuel_type', car.fuel_type).strip()
                valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
                if fuel_type in valid_fuel_types:
                    car.fuel_type = fuel_type
                else:
                    return JsonResponse(
                        {
                            'success': False,
                            'message': f'Invalid fuel type. Valid types: {", ".join(valid_fuel_types)}',
                        },
                        status=400,
                    )
            if 'mileage' in request.POST:
                car.mileage = request.POST.get('mileage', car.mileage)
            if 'rating' in request.POST:
                rating = request.POST.get('rating', '').strip()
                car.rating = rating or None
            if 'review_count' in request.POST:
                car.review_count = request.POST.get('review_count', car.review_count)
            if 'features' in request.POST:
                features_raw = request.POST.get('features', '').strip()
                features = []
                if features_raw:
                    try:
                        parsed = json.loads(features_raw)
                        if isinstance(parsed, list):
                            features = parsed
                    except json.JSONDecodeError:
                        features = [item.strip() for item in features_raw.split(',') if item.strip()]
                car.features = features
            if 'car_image_url' in request.POST:
                car.car_image_url = request.POST.get('car_image_url', car.car_image_url).strip()
            if 'is_available' in request.POST:
                is_available_raw = request.POST.get('is_available', str(car.is_available)).strip().lower()
                car.is_available = is_available_raw in ('true', '1', 'yes', 'on')

        else:
            # Original JSON-based API
            data = json.loads(request.body.decode('utf-8'))

            # Update fields if provided
            updatable_fields = [
                'model', 'type', 'company', 'price_per_day', 'original_price',
                'car_image_url', 'transmission', 'seats', 'luggage_capacity',
                'fuel_type', 'mileage', 'rating', 'review_count', 'features', 'is_available'
            ]

            for field in updatable_fields:
                if field in data:
                    setattr(car, field, data[field])

        car.save()

        return JsonResponse(
            {
                'success': True,
                'message': 'Car updated successfully',
            },
            status=200
        )

    except Car.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Car not found'},
            status=404
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON data'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)},
            status=400
        )


@csrf_exempt
@require_http_methods(['DELETE'])
def car_delete_api(request, car_id):
    """Delete a car (admin only)."""
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    try:
        car = Car.objects.get(id=car_id)
        car.delete()
        
        return JsonResponse(
            {
                'success': True,
                'message': 'Car deleted successfully',
            },
            status=200
        )
    
    except Car.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Car not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)},
            status=400
        )




# === Package API Endpoints ===


@csrf_exempt
@require_http_methods(['GET'])
def package_admin_list_api(request):
    """
    Get all packages for admin management (Super Admin only).
    Includes both active and inactive packages.
    """
    # Check if user is super admin
    is_auth, user = check_admin_auth(request)
    if not is_auth:
        return JsonResponse(
            {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
            status=403
        )
    
    packages = Package.objects.all().order_by('-created_at')
    
    results = []
    for package in packages:
        results.append({
            'id': package.id,
            'title': package.title,
            'destination': package.destination,
            'description': package.description,
            'hotel': {
                'name': package.hotel_name,
                'location': package.hotel_location,
                'image': package.hotel_image_url,
                'stars': package.hotel_stars,
                'rating': float(package.hotel_rating),
                'reviewCount': package.hotel_review_count,
            },
            'flight': {
                'airline': package.airline,
                'departure': {
                    'code': package.departure_airport,
                    'time': package.departure_time,
                },
                'arrival': {
                    'code': package.arrival_airport,
                    'time': package.arrival_time,
                },
                'duration': package.flight_duration,
                'stops': package.flight_stops,
            },
            'price': float(package.price_per_person),
            'originalPrice': float(package.original_price) if package.original_price else None,
            'pricePer': 'person',
            'nights': package.nights,
            'highlights': package.highlights,
            'packageType': package.get_package_type_display(),
            'includes': package.includes,
            'discount_percentage': package.discount_percentage,
            'is_featured': package.is_featured,
            'is_popular': package.is_popular,
            'is_active': package.is_active,
            'status': package.status,
            'created_at': package.created_at.isoformat(),
            'updated_at': package.updated_at.isoformat(),
        })
    
    return JsonResponse(
        {
            'success': True,
            'packages': results,
            'count': len(results),
        },
        status=200
    )


@csrf_exempt
@require_http_methods(['GET'])
def package_list_api(request):
        """List all available packages with filtering options."""
        try:
            # Get query parameters
            destination = request.GET.get('destination')
            package_type = request.GET.get('type')
            min_price = request.GET.get('min_price')
            max_price = request.GET.get('max_price')
            
            # Base query - only active packages
            packages = Package.objects.filter(is_active=True, status='active')
            
            # Apply filters
            if destination:
                packages = packages.filter(
                    Q(destination__icontains=destination) | Q(title__icontains=destination)
                )
            
            if package_type:
                packages = packages.filter(package_type=package_type)
            
            if min_price:
                packages = packages.filter(price_per_person__gte=min_price)
            
            if max_price:
                packages = packages.filter(price_per_person__lte=max_price)
            
            # Sorting options
            sort_by = request.GET.get('sort_by', 'popularity')
            if sort_by == 'price_low':
                packages = packages.order_by('price_per_person')
            elif sort_by == 'price_high':
                packages = packages.order_by('-price_per_person')
            elif sort_by == 'rating':
                packages = packages.order_by('-hotel_rating')
            elif sort_by == 'nights':
                packages = packages.order_by('-nights')
            else:  # popularity
                packages = packages.order_by('-bookings')
            
            # Prepare results
            results = []
            for package in packages:
                results.append({
                    'id': package.id,
                    'title': package.title,
                    'destination': package.destination,
                    'description': package.description,
                    'hotel': {
                        'name': package.hotel_name,
                        'location': package.hotel_location,
                        'image': package.hotel_image_url,
                        'stars': package.hotel_stars,
                        'rating': float(package.hotel_rating),
                        'reviewCount': package.hotel_review_count,
                    },
                    'flight': {
                        'airline': package.airline,
                        'departure': {
                            'code': package.departure_airport,
                            'time': package.departure_time,
                        },
                        'arrival': {
                            'code': package.arrival_airport,
                            'time': package.arrival_time,
                        },
                        'duration': package.flight_duration,
                        'stops': package.flight_stops,
                    },
                    'price': float(package.price_per_person),
                    'originalPrice': float(package.original_price) if package.original_price else None,
                    'pricePer': 'person',
                    'nights': package.nights,
                    'highlights': package.highlights,
                    'packageType': package.get_package_type_display(),
                    'includes': package.includes,
                    'discount_percentage': package.discount_percentage,
                    'is_featured': package.is_featured,
                    'is_popular': package.is_popular,
                    'created_at': package.created_at.isoformat(),
                    'updated_at': package.updated_at.isoformat(),
                })
            
            return JsonResponse(
                {
                    'success': True,
                    'packages': results,
                    'count': len(results),
                },
                status=200
            )
        
        except Exception as e:
            return JsonResponse(
                {'success': False, 'message': str(e)},
                status=400
            )
    
    


@csrf_exempt
@require_http_methods(['GET'])
def package_detail_api(request, package_id):
        """Get specific package details by ID."""
        try:
            package = Package.objects.get(id=package_id, is_active=True, status='active')
            
            package_data = {
                'id': package.id,
                'title': package.title,
                'destination': package.destination,
                'description': package.description,
                'hotel': {
                    'name': package.hotel_name,
                    'location': package.hotel_location,
                    'image': package.hotel_image_url,
                    'stars': package.hotel_stars,
                    'rating': float(package.hotel_rating),
                    'reviewCount': package.hotel_review_count,
                },
                'flight': {
                    'airline': package.airline,
                    'departure': {
                        'code': package.departure_airport,
                        'time': package.departure_time,
                    },
                    'arrival': {
                        'code': package.arrival_airport,
                        'time': package.arrival_time,
                    },
                    'duration': package.flight_duration,
                    'stops': package.flight_stops,
                },
                'price': float(package.price_per_person),
                'originalPrice': float(package.original_price) if package.original_price else None,
                'pricePer': 'person',
                'nights': package.nights,
                'highlights': package.highlights,
                'packageType': package.get_package_type_display(),
                'includes': package.includes,
                'discount_percentage': package.discount_percentage,
                'is_featured': package.is_featured,
                'is_popular': package.is_popular,
                'availability': package.availability,
                'bookings': package.bookings,
                'remaining_availability': package.remaining_availability,
                'status': package.status,
                'created_at': package.created_at.isoformat(),
                'updated_at': package.updated_at.isoformat(),
            }
            
            return JsonResponse(
                {
                    'success': True,
                    'package': package_data,
                },
                status=200
            )
            
        except Package.DoesNotExist:
            return JsonResponse(
                {'success': False, 'message': 'Package not found'},
                status=404
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'message': str(e)},
                status=400
            )
    
    


@csrf_exempt
@require_http_methods(['POST'])
def package_create_api(request):
        """Create a new package (admin only).
            
        Supports image upload to Cloudinary.
        """
        # Check if user is super admin
        is_auth, user = check_admin_auth(request)
        if not is_auth:
            return JsonResponse(
                {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
                status=403
            )
        
        try:
            # Handle multipart form data for file upload
            if request.content_type.startswith('multipart/form-data'):
                # Extract JSON data from form
                title = request.POST.get('title', '').strip()
                destination = request.POST.get('destination', '').strip()
                hotel_name = request.POST.get('hotel_name', '').strip()
                hotel_location = request.POST.get('hotel_location', '').strip()
                airline = request.POST.get('airline', '').strip()
                departure_airport = request.POST.get('departure_airport', '').strip()
                arrival_airport = request.POST.get('arrival_airport', '').strip()
                price_per_person = request.POST.get('price_per_person', '')
                nights = request.POST.get('nights', '')
                package_type = request.POST.get('package_type', '').strip()
                    
                # Required fields validation
                required_fields = [
                    (title, 'title'), (destination, 'destination'), (hotel_name, 'hotel_name'), 
                    (hotel_location, 'hotel_location'), (airline, 'airline'), 
                    (departure_airport, 'departure_airport'), (arrival_airport, 'arrival_airport'),
                    (price_per_person, 'price_per_person'), (nights, 'nights'), (package_type, 'package_type')
                ]
                for field_value, field_name in required_fields:
                    if not field_value:
                        return JsonResponse(
                            {'success': False, 'message': f'{field_name} is required'},
                            status=400
                        )
                    
                # Parse numeric fields
                try:
                    price_per_person = float(price_per_person)
                    nights = int(nights)
                except ValueError:
                    return JsonResponse(
                        {'success': False, 'message': 'Price per person must be a number and nights must be an integer'},
                        status=400
                    )
                    
                # Validate package type
                valid_types = [choice[0] for choice in Package.PACKAGE_TYPES]
                if package_type not in valid_types:
                    return JsonResponse(
                        {'success': False, 'message': f'Invalid package type. Valid types: {", ".join(valid_types)}'},
                        status=400
                    )
                
                # Validate field lengths to prevent database errors
                if len(departure_airport) > 10:
                    return JsonResponse(
                        {'success': False, 'message': 'Departure airport code must be 10 characters or less'},
                        status=400
                    )
                if len(arrival_airport) > 10:
                    return JsonResponse(
                        {'success': False, 'message': 'Arrival airport code must be 10 characters or less'},
                        status=400
                    )
                    
                # Handle image upload to Cloudinary
                hotel_image_url = ''
                if 'hotel_image' in request.FILES:
                    try:
                        # Import cloudinary here to ensure config is loaded
                        import cloudinary.uploader
                        upload_result = cloudinary.uploader.upload(
                            request.FILES['hotel_image'],
                            folder='packages/',
                            resource_type='image'
                        )
                        hotel_image_url = upload_result.get('secure_url', '')
                    except Exception as e:
                        # Log the error but don't fail - create package without image
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Cloudinary upload failed: {str(e)}')
                        # Continue without image - package will be created without an image URL
                        hotel_image_url = ''
                    
                # Get other optional fields
                description = request.POST.get('description', '')
                hotel_stars = request.POST.get('hotel_stars', '3')
                hotel_rating = request.POST.get('hotel_rating', '0.00')
                hotel_review_count = request.POST.get('hotel_review_count', '0')
                flight_duration = request.POST.get('flight_duration', '')
                flight_stops = request.POST.get('flight_stops', '0')
                departure_time = request.POST.get('departure_time', '').strip()
                arrival_time = request.POST.get('arrival_time', '').strip()
                original_price = request.POST.get('original_price')
                price_per_package = request.POST.get('price_per_package')
                highlights = request.POST.get('highlights', '[]')
                includes = request.POST.get('includes', '[]')
                availability = request.POST.get('availability', '0')
                bookings = request.POST.get('bookings', '0')
                is_featured = request.POST.get('is_featured', 'false').lower() in ('true', '1', 'yes')
                is_popular = request.POST.get('is_popular', 'false').lower() in ('true', '1', 'yes')
                is_active = request.POST.get('is_active', 'true').lower() in ('true', '1', 'yes')
                status = request.POST.get('status', 'active')
                
                # Validate time field lengths
                if len(departure_time) > 10:
                    return JsonResponse(
                        {'success': False, 'message': 'Departure time must be 10 characters or less (e.g., 08:30)'},
                        status=400
                    )
                if len(arrival_time) > 10:
                    return JsonResponse(
                        {'success': False, 'message': 'Arrival time must be 10 characters or less (e.g., 21:45)'},
                        status=400
                    )
                    
                # Validate status if provided
                valid_statuses = ['draft', 'active', 'inactive', 'expired']
                if status not in valid_statuses:
                    return JsonResponse(
                        {'success': False, 'message': f'Invalid status. Valid statuses: {", ".join(valid_statuses)}'},
                        status=400
                    )
                    
                # Convert numeric fields
                try:
                    hotel_stars = int(hotel_stars)
                    if not 1 <= hotel_stars <= 5:
                        raise ValueError('Stars must be between 1 and 5')
                except ValueError:
                    return JsonResponse(
                        {'success': False, 'message': 'Hotel stars must be between 1 and 5'},
                        status=400
                    )
                    
                try:
                    hotel_rating = float(hotel_rating)
                    if not 0 <= hotel_rating <= 5:
                        raise ValueError('Rating must be between 0 and 5')
                except ValueError:
                    return JsonResponse(
                        {'success': False, 'message': 'Hotel rating must be between 0 and 5'},
                        status=400
                    )
                    
                try:
                    hotel_review_count = int(hotel_review_count)
                    if hotel_review_count < 0:
                        raise ValueError('Review count must be non-negative')
                except ValueError:
                    return JsonResponse(
                        {'success': False, 'message': 'Hotel review count must be a non-negative integer'},
                        status=400
                    )
                    
                try:
                    flight_stops = int(flight_stops)
                except ValueError:
                    return JsonResponse(
                        {'success': False, 'message': 'Flight stops must be an integer'},
                        status=400
                    )
                    
                try:
                    availability = int(availability)
                    bookings = int(bookings)
                except ValueError:
                    return JsonResponse(
                        {'success': False, 'message': 'Availability and bookings must be integers'},
                        status=400
                    )
                    
                # Parse JSON arrays
                import json
                try:
                    highlights = json.loads(highlights) if highlights.strip() else []
                    if not isinstance(highlights, list):
                        highlights = []
                except json.JSONDecodeError:
                    # Try parsing as comma-separated string
                    highlights = [item.strip() for item in highlights.split(',') if item.strip()]
                    
                try:
                    includes = json.loads(includes) if includes.strip() else []
                    if not isinstance(includes, list):
                        includes = []
                except json.JSONDecodeError:
                    # Try parsing as comma-separated string
                    includes = [item.strip() for item in includes.split(',') if item.strip()]
                    
                # Create package
                package = Package.objects.create(
                    title=title,
                    destination=destination,
                    description=description,
                    hotel_name=hotel_name,
                    hotel_location=hotel_location,
                    hotel_stars=hotel_stars,
                    hotel_rating=hotel_rating,
                    hotel_review_count=hotel_review_count,
                    hotel_image_url=hotel_image_url,
                    airline=airline,
                    departure_airport=departure_airport,
                    arrival_airport=arrival_airport,
                    flight_duration=flight_duration,
                    flight_stops=flight_stops,
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    price_per_person=price_per_person,
                    original_price=original_price,
                    price_per_package=price_per_package,
                    nights=nights,
                    package_type=package_type,
                    highlights=highlights,
                    includes=includes,
                    availability=availability,
                    bookings=bookings,
                    is_featured=is_featured,
                    is_popular=is_popular,
                    is_active=is_active,
                    status=status,
                )
                    
                return JsonResponse(
                    {
                        'success': True,
                        'message': 'Package created successfully',
                        'package_id': package.id,
                    },
                    status=201
                )
            else:
                # Original JSON handling code for backward compatibility
                data = json.loads(request.body)
                    
                # Required fields
                required_fields = [
                    'title', 'destination', 'hotel_name', 'hotel_location',
                    'airline', 'departure_airport', 'arrival_airport',
                    'price_per_person', 'nights', 'package_type'
                ]
                for field in required_fields:
                    if field not in data:
                        return JsonResponse(
                            {'success': False, 'message': f'{field} is required'},
                            status=400
                        )
                    
                # Validate package type
                valid_types = [choice[0] for choice in Package.PACKAGE_TYPES]
                if data['package_type'] not in valid_types:
                    return JsonResponse(
                        {'success': False, 'message': f'Invalid package type. Valid types: {", ".join(valid_types)}'},
                        status=400
                    )
                    
                # Validate status if provided
                valid_statuses = ['draft', 'active', 'inactive', 'expired']
                if 'status' in data and data['status'] not in valid_statuses:
                    return JsonResponse(
                        {'success': False, 'message': f'Invalid status. Valid statuses: {", ".join(valid_statuses)}'},
                        status=400
                    )
                    
                # Create package
                package = Package.objects.create(
                    title=data['title'],
                    destination=data['destination'],
                    description=data.get('description', ''),
                    hotel_name=data['hotel_name'],
                    hotel_location=data['hotel_location'],
                    hotel_stars=data.get('hotel_stars', 3),
                    hotel_rating=data.get('hotel_rating', 0.00),
                    hotel_review_count=data.get('hotel_review_count', 0),
                    hotel_image_url=data.get('hotel_image_url', ''),
                    airline=data['airline'],
                    departure_airport=data['departure_airport'],
                    arrival_airport=data['arrival_airport'],
                    flight_duration=data.get('flight_duration', ''),
                    flight_stops=data.get('flight_stops', 0),
                    departure_time=data.get('departure_time', ''),
                    arrival_time=data.get('arrival_time', ''),
                    price_per_person=data['price_per_person'],
                    original_price=data.get('original_price'),
                    price_per_package=data.get('price_per_package'),
                    nights=data['nights'],
                    package_type=data['package_type'],
                    highlights=data.get('highlights', []),
                    includes=data.get('includes', []),
                    availability=data.get('availability', 0),
                    bookings=data.get('bookings', 0),
                    is_featured=data.get('is_featured', False),
                    is_popular=data.get('is_popular', False),
                    is_active=data.get('is_active', True),
                    status=data.get('status', 'active'),
                )
                    
                return JsonResponse(
                    {
                        'success': True,
                        'message': 'Package created successfully',
                        'package_id': package.id,
                    },
                    status=201
                )
        except json.JSONDecodeError:
            return JsonResponse(
                {'success': False, 'message': 'Invalid JSON data'},
                status=400
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'message': str(e)},
                status=400
            )
    
    


@csrf_exempt
@require_http_methods(['POST'])
def package_update_api(request, package_id):
        """Update an existing package (admin only).
            
        Supports image upload to Cloudinary.
        """
        # Check if user is super admin
        is_auth, user = check_admin_auth(request)
        if not is_auth:
            return JsonResponse(
                {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
                status=403
            )
        
        try:
            package = Package.objects.get(id=package_id)
                
            # Handle multipart form data for file upload
            if request.content_type.startswith('multipart/form-data'):
                # Extract form data
                title = request.POST.get('title', '').strip()
                destination = request.POST.get('destination', '').strip()
                hotel_name = request.POST.get('hotel_name', '').strip()
                hotel_location = request.POST.get('hotel_location', '').strip()
                airline = request.POST.get('airline', '').strip()
                departure_airport = request.POST.get('departure_airport', '').strip()
                arrival_airport = request.POST.get('arrival_airport', '').strip()
                price_per_person = request.POST.get('price_per_person', '')
                nights = request.POST.get('nights', '')
                package_type = request.POST.get('package_type', '').strip()
                    
                # Handle image upload to Cloudinary
                if 'hotel_image' in request.FILES:
                    try:
                        # Import cloudinary here to ensure config is loaded
                        import cloudinary.uploader
                        upload_result = cloudinary.uploader.upload(
                            request.FILES['hotel_image'],
                            folder='packages/',
                            resource_type='image'
                        )
                        package.hotel_image_url = upload_result.get('secure_url', '')
                    except Exception as e:
                        # Log the error but don't fail - update package without new image
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f'Cloudinary upload failed: {str(e)}')
                        # Continue without updating image
                    
                # Update fields if provided
                if title:
                    package.title = title
                if destination:
                    package.destination = destination
                if hotel_name:
                    package.hotel_name = hotel_name
                if hotel_location:
                    package.hotel_location = hotel_location
                if airline:
                    package.airline = airline
                if departure_airport:
                    if len(departure_airport) > 10:
                        return JsonResponse(
                            {'success': False, 'message': 'Departure airport code must be 10 characters or less'},
                            status=400
                        )
                    package.departure_airport = departure_airport
                if arrival_airport:
                    if len(arrival_airport) > 10:
                        return JsonResponse(
                            {'success': False, 'message': 'Arrival airport code must be 10 characters or less'},
                            status=400
                        )
                    package.arrival_airport = arrival_airport
                    
                # Convert and update numeric fields
                if price_per_person:
                    try:
                        package.price_per_person = float(price_per_person)
                    except ValueError:
                        return JsonResponse(
                            {'success': False, 'message': 'Price per person must be a number'},
                            status=400
                        )
                    
                if nights:
                    try:
                        package.nights = int(nights)
                    except ValueError:
                        return JsonResponse(
                            {'success': False, 'message': 'Nights must be an integer'},
                            status=400
                        )
                    
                if package_type:
                    valid_types = [choice[0] for choice in Package.PACKAGE_TYPES]
                    if package_type in valid_types:
                        package.package_type = package_type
                    else:
                        return JsonResponse(
                            {'success': False, 'message': f'Invalid package type. Valid types: {", ".join(valid_types)}'},
                            status=400
                        )
                    
                # Update other optional fields
                if 'description' in request.POST:
                    package.description = request.POST.get('description', '')
                    
                if 'hotel_stars' in request.POST:
                    try:
                        stars = int(request.POST.get('hotel_stars', str(package.hotel_stars)))
                        if 1 <= stars <= 5:
                            package.hotel_stars = stars
                    except ValueError:
                        pass
                    
                if 'hotel_rating' in request.POST:
                    try:
                        rating = float(request.POST.get('hotel_rating', str(package.hotel_rating)))
                        if 0 <= rating <= 5:
                            package.hotel_rating = rating
                    except ValueError:
                        pass
                    
                if 'hotel_review_count' in request.POST:
                    try:
                        review_count = int(request.POST.get('hotel_review_count', str(package.hotel_review_count)))
                        if review_count >= 0:
                            package.hotel_review_count = review_count
                    except ValueError:
                        pass
                    
                if 'flight_duration' in request.POST:
                    package.flight_duration = request.POST.get('flight_duration', '')
                    
                if 'flight_stops' in request.POST:
                    try:
                        stops = int(request.POST.get('flight_stops', str(package.flight_stops)))
                        package.flight_stops = stops
                    except ValueError:
                        pass
                    
                if 'departure_time' in request.POST:
                    departure_time = request.POST.get('departure_time', '').strip()
                    if len(departure_time) > 10:
                        return JsonResponse(
                            {'success': False, 'message': 'Departure time must be 10 characters or less (e.g., 08:30)'},
                            status=400
                        )
                    package.departure_time = departure_time
                    
                if 'arrival_time' in request.POST:
                    arrival_time = request.POST.get('arrival_time', '').strip()
                    if len(arrival_time) > 10:
                        return JsonResponse(
                            {'success': False, 'message': 'Arrival time must be 10 characters or less (e.g., 21:45)'},
                            status=400
                        )
                    package.arrival_time = arrival_time
                    
                if 'original_price' in request.POST:
                    original_price = request.POST.get('original_price')
                    if original_price:
                        try:
                            package.original_price = float(original_price)
                        except ValueError:
                            return JsonResponse(
                                {'success': False, 'message': 'Original price must be a number'},
                                status=400
                            )
                    else:
                        package.original_price = None
                    
                if 'price_per_package' in request.POST:
                    price_per_package = request.POST.get('price_per_package')
                    if price_per_package:
                        try:
                            package.price_per_package = float(price_per_package)
                        except ValueError:
                            return JsonResponse(
                                {'success': False, 'message': 'Price per package must be a number'},
                                status=400
                            )
                    else:
                        package.price_per_package = None
                    
                # Parse and update JSON arrays
                if 'highlights' in request.POST:
                    highlights = request.POST.get('highlights', '[]')
                    import json
                    try:
                        parsed_highlights = json.loads(highlights) if highlights.strip() else []
                        if isinstance(parsed_highlights, list):
                            package.highlights = parsed_highlights
                    except json.JSONDecodeError:
                        # Try parsing as comma-separated string
                        parsed_highlights = [item.strip() for item in highlights.split(',') if item.strip()]
                        package.highlights = parsed_highlights
                    
                if 'includes' in request.POST:
                    includes = request.POST.get('includes', '[]')
                    import json
                    try:
                        parsed_includes = json.loads(includes) if includes.strip() else []
                        if isinstance(parsed_includes, list):
                            package.includes = parsed_includes
                    except json.JSONDecodeError:
                        # Try parsing as comma-separated string
                        parsed_includes = [item.strip() for item in includes.split(',') if item.strip()]
                        package.includes = parsed_includes
                    
                if 'availability' in request.POST:
                    try:
                        availability = int(request.POST.get('availability', str(package.availability)))
                        package.availability = availability
                    except ValueError:
                        pass
                    
                if 'bookings' in request.POST:
                    try:
                        bookings = int(request.POST.get('bookings', str(package.bookings)))
                        package.bookings = bookings
                    except ValueError:
                        pass
                    
                if 'is_featured' in request.POST:
                    package.is_featured = request.POST.get('is_featured', str(package.is_featured)).lower() in ('true', '1', 'yes')
                    
                if 'is_popular' in request.POST:
                    package.is_popular = request.POST.get('is_popular', str(package.is_popular)).lower() in ('true', '1', 'yes')
                    
                if 'is_active' in request.POST:
                    package.is_active = request.POST.get('is_active', str(package.is_active)).lower() in ('true', '1', 'yes')
                    
                if 'status' in request.POST:
                    status_val = request.POST.get('status', package.status)
                    valid_statuses = ['draft', 'active', 'inactive', 'expired']
                    if status_val in valid_statuses:
                        package.status = status_val
                    else:
                        return JsonResponse(
                            {'success': False, 'message': f'Invalid status. Valid statuses: {", ".join(valid_statuses)}'},
                            status=400
                        )
                    
                package.save()
                    
                return JsonResponse(
                    {
                        'success': True,
                        'message': 'Package updated successfully',
                    },
                    status=200
                )
            else:
                # Original JSON handling code for backward compatibility
                data = json.loads(request.body)
                    
                # Update fields if provided
                updatable_fields = [
                    'title', 'destination', 'description', 'hotel_name', 'hotel_location',
                    'hotel_stars', 'hotel_rating', 'hotel_review_count', 'hotel_image_url',
                    'airline', 'departure_airport', 'arrival_airport', 'flight_duration',
                    'flight_stops', 'departure_time', 'arrival_time', 'price_per_person',
                    'original_price', 'price_per_package', 'nights', 'package_type',
                    'highlights', 'includes', 'availability', 'bookings', 'is_featured',
                    'is_popular', 'is_active', 'status'
                ]
                    
                for field in updatable_fields:
                    if field in data:
                        setattr(package, field, data[field])
                    
                package.save()
                    
                return JsonResponse(
                    {
                        'success': True,
                        'message': 'Package updated successfully',
                    },
                    status=200
                )
            
        except Package.DoesNotExist:
            return JsonResponse(
                {'success': False, 'message': 'Package not found'},
                status=404
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {'success': False, 'message': 'Invalid JSON data'},
                status=400
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'message': str(e)},
                status=400
            )
    
    


@csrf_exempt
@require_http_methods(['DELETE'])
def package_delete_api(request, package_id):
        """Delete a package (admin only)."""
        # Check if user is super admin
        is_auth, user = check_admin_auth(request)
        if not is_auth:
            return JsonResponse(
                {'success': False, 'message': 'Unauthorized. Super Admin access required.'},
                status=403
            )
        
        try:
            package = Package.objects.get(id=package_id)
            package.delete()
            
            return JsonResponse(
                {
                    'success': True,
                    'message': 'Package deleted successfully',
                },
                status=200
            )
            
        except Package.DoesNotExist:
            return JsonResponse(
                {'success': False, 'message': 'Package not found'},
                status=404
            )
        except Exception as e:
            return JsonResponse(
                {'success': False, 'message': str(e)},
                status=400
            )


# ==================== AI CHAT & ITINERARY APIs ====================


@csrf_exempt
@require_http_methods(['POST'])
def ai_chat_api(request):
    """
    AI Travel Assistant chat endpoint.

    Request JSON body:
    - message: str (required) – latest user message
    - sessionId: str (optional) – existing ChatSession ID to continue
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON body.'},
            status=400,
        )

    message = (body.get('message') or '').strip()
    if not message:
        return JsonResponse(
            {'success': False, 'message': 'Field "message" is required.'},
            status=400,
        )

    raw_session_id = body.get('sessionId') or body.get('session_id')
    user = request.user if request.user.is_authenticated else None

    # Prepare / create session and store the user message
    with transaction.atomic():
        session: ChatSession
        if raw_session_id:
            try:
                session = ChatSession.objects.select_for_update().get(pk=raw_session_id)
                if user and session.user and session.user_id != user.id:
                    return JsonResponse(
                        {
                            'success': False,
                            'message': 'You do not have access to this chat session.',
                        },
                        status=403,
                    )
                if user and session.user is None:
                    session.user = user
                    session.save(update_fields=['user'])
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create(
                    user=user if getattr(user, 'is_authenticated', False) else None,
                    session_type='chat',
                )
        else:
            session = ChatSession.objects.create(
                user=user if getattr(user, 'is_authenticated', False) else None,
                session_type='chat',
            )

        previous_messages = list(
            ChatMessage.objects.filter(session=session).order_by('created_at')
        )[-20:]

        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=message,
            metadata={},
        )

    history_for_ai = previous_messages + [user_message]

    try:
        ai_payload = generate_chat_reply(
            user=user,
            session=session,
            user_message=message,
            previous_messages=history_for_ai,
        )
    except AIConfigurationError as exc:
        return JsonResponse(
            {
                'success': False,
                'message': str(exc),
            },
            status=503,
        )
    except AIServiceError as exc:
        return JsonResponse(
            {
                'success': False,
                'message': str(exc),
            },
            status=503,
        )
    except Exception as exc:  # noqa: BLE001
        # Catch-all to avoid leaking internal errors to the client
        return JsonResponse(
            {
                'success': False,
                'message': 'Unexpected error while generating AI response.',
            },
            status=500,
        )

    ai_text = (ai_payload.get('message') or '').strip()
    quick_replies = ai_payload.get('quickReplies') or []

    # Persist assistant message and minimal metadata
    with transaction.atomic():
        assistant_message = ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=ai_text,
            metadata={
                'quick_replies': quick_replies,
                'recommendations': ai_payload.get('recommendations'),
                'context_summary': ai_payload.get('context'),
            },
        )

    return JsonResponse(
        {
            'success': True,
            'sessionId': str(session.pk),
            'message': ai_text,
            'quickReplies': quick_replies,
            'needsFollowUp': bool(ai_payload.get('needsFollowUp')),
            'context': ai_payload.get('context') or {},
            'recommendations': ai_payload.get('recommendations') or {},
        },
        status=200,
    )


@csrf_exempt
@require_http_methods(['POST'])
def ai_itinerary_api(request):
    """
    AI-based itinerary generator endpoint.

    Request JSON body:
    - destination: str (required)
    - start_date: YYYY-MM-DD (required)
    - end_date: YYYY-MM-DD (required)
    - budget: number (optional)
    - preferences: str (optional)
    - travelers: int (optional)
    - sessionId: str (optional) – to link with an existing chat session
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON body.'},
            status=400,
        )

    destination = (body.get('destination') or '').strip()
    start_date = (body.get('start_date') or '').strip()
    end_date = (body.get('end_date') or '').strip()

    if not destination or not start_date or not end_date:
        return JsonResponse(
            {
                'success': False,
                'message': 'destination, start_date and end_date are required.',
            },
            status=400,
        )

    session: ChatSession | None = None
    raw_session_id = body.get('sessionId') or body.get('session_id')
    user = request.user if request.user.is_authenticated else None

    if raw_session_id:
        try:
            session = ChatSession.objects.get(pk=raw_session_id)
        except ChatSession.DoesNotExist:
            session = None

    try:
        itinerary_instance = generate_itinerary(
            user=user,
            session=session,
            form_data=body,
        )
    except AIConfigurationError as exc:
        return JsonResponse(
            {
                'success': False,
                'message': str(exc),
            },
            status=503,
        )
    except AIServiceError as exc:
        return JsonResponse(
            {
                'success': False,
                'message': str(exc),
            },
            status=503,
        )
    except Exception:
        return JsonResponse(
            {
                'success': False,
                'message': 'Unexpected error while generating itinerary.',
            },
            status=500,
        )

    return JsonResponse(
        {
            'success': True,
            'itineraryId': itinerary_instance.pk,
            'itinerary': itinerary_instance.public_payload,
        },
        status=200,
    )


@require_http_methods(['GET'])
def ai_itinerary_detail_api(request, itinerary_id: int):
    """
    Fetch a previously generated itinerary by ID for the detail page.
    """
    try:
        itinerary = GeneratedItinerary.objects.get(pk=itinerary_id)
    except GeneratedItinerary.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Itinerary not found.'},
            status=404,
        )

    user = request.user if request.user.is_authenticated else None
    if itinerary.user and user and itinerary.user_id != user.id:
        return JsonResponse(
            {'success': False, 'message': 'You do not have access to this itinerary.'},
            status=403,
        )

    return JsonResponse(
        {
            'success': True,
            'itinerary': itinerary.public_payload,
        },
        status=200,
    )
