"""
S3 image upload utility (via boto3 + django-storages fallback).

Saves uploaded images to AWS S3 and returns the public HTTPS URL.
"""

import os
import sys
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def _reset_file_pointer(uploaded_file) -> None:
    if hasattr(uploaded_file, 'seek'):
        try:
            uploaded_file.seek(0)
        except Exception:
            pass


def _s3_public_url(key: str) -> str:
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    region = getattr(settings, 'AWS_S3_REGION_NAME', 'eu-north-1')
    custom = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
    if custom:
        return f'https://{custom}/{key}'
    return f'https://{bucket}.s3.{region}.amazonaws.com/{key}'


def _upload_via_boto3(uploaded_file, path: str) -> str:
    import boto3
    from botocore.config import Config

    _reset_file_pointer(uploaded_file)
    client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3v4'),
    )
    content_type = getattr(uploaded_file, 'content_type', None) or 'image/jpeg'
    extra_args = {'ContentType': content_type}
    client.upload_fileobj(
        uploaded_file,
        settings.AWS_STORAGE_BUCKET_NAME,
        path,
        ExtraArgs=extra_args,
    )
    return _s3_public_url(path)


def save_uploaded_image(uploaded_file, subfolder='uploads'):
    """
    Save an uploaded file to S3 (or local media as fallback).

    Returns:
        str: Public HTTPS URL, or '' if save fails.
    """
    ext = os.path.splitext(uploaded_file.name)[1] or '.jpg'
    filename = f'{uuid.uuid4().hex}{ext}'
    path = f'{subfolder}/{filename}'

    if getattr(settings, 'USE_S3', False) and settings.AWS_ACCESS_KEY_ID:
        try:
            url = _upload_via_boto3(uploaded_file, path)
            print(f'Image uploaded to S3: {url}', file=sys.stderr)
            return url
        except Exception as e:
            print(f'S3 boto3 upload failed: {e}', file=sys.stderr)

    _reset_file_pointer(uploaded_file)
    try:
        from django.core.files.storage import default_storage
        saved_path = default_storage.save(path, uploaded_file)
        url = default_storage.url(saved_path)
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        print(f'Image uploaded via storage backend: {url}', file=sys.stderr)
        return url
    except Exception as e:
        print(f'Storage backend upload failed: {e}', file=sys.stderr)

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


def resolve_image_url_after_upload(uploaded_file, subfolder: str, fallback_url: str = '') -> tuple[str, str | None]:
    """
    Try upload; return (url, warning_message).
    Uses fallback_url (e.g. from form) when upload fails.
    """
    url = ''
    if uploaded_file:
        url = save_uploaded_image(uploaded_file, subfolder=subfolder)
    if url:
        return url, None
    fallback = (fallback_url or '').strip()
    if fallback:
        return fallback, 'Image file could not be uploaded to S3; saved using the image URL from the form.'
    if uploaded_file:
        return '', 'Image upload failed. Add S3 PutObject permission to your IAM user, or paste an image URL in the form.'
    return '', None
