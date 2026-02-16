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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services.amadeus import AmadeusError, search_flights
from .models import City, Hotel, Room

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
