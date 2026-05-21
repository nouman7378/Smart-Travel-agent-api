"""
S3 image upload utility (via django-storages).

Saves uploaded images to AWS S3 and returns the public URL.
Falls back to local file storage when S3 is not configured.
"""

import os
import sys
import uuid

from django.conf import settings
from django.core.files.storage import default_storage, FileSystemStorage


def _reset_file_pointer(uploaded_file) -> None:
    if hasattr(uploaded_file, 'seek'):
        try:
            uploaded_file.seek(0)
        except Exception:
            pass


def save_uploaded_image(uploaded_file, subfolder='uploads'):
    """
    Save an uploaded file to S3 (or local media as fallback).

    Args:
        uploaded_file: Django UploadedFile (from request.FILES)
        subfolder: S3 key prefix (e.g. 'hotels', 'rooms', 'packages', 'cars')

    Returns:
        str: Public HTTPS URL, or '' if save fails.
    """
    ext = os.path.splitext(uploaded_file.name)[1] or '.jpg'
    filename = f'{uuid.uuid4().hex}{ext}'
    path = f'{subfolder}/{filename}'

    _reset_file_pointer(uploaded_file)
    try:
        saved_path = default_storage.save(path, uploaded_file)
        url = default_storage.url(saved_path)
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        print(f'Image uploaded: {url}', file=sys.stderr)
        return url
    except Exception as e:
        print(f'S3/default storage upload failed: {e}. Trying local fallback...', file=sys.stderr)

    if getattr(settings, 'USE_S3', False):
        return ''

    _reset_file_pointer(uploaded_file)
    try:
        fs = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
        saved_name = fs.save(path, uploaded_file)
        local_url = fs.url(saved_name)
        if local_url.startswith('/'):
            base = getattr(settings, 'SITE_BASE_URL', '').rstrip('/')
            local_url = f'{base}{local_url}' if base else local_url
        print(f'Image saved locally: {local_url}', file=sys.stderr)
        return local_url
    except Exception as local_err:
        print(f'Local storage fallback failed: {local_err}', file=sys.stderr)
        return ''
