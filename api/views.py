"""
API views for Smart-Travel-Planner backend.
"""
import re

import json

from django.contrib.auth import authenticate, get_user_model, login
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

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
