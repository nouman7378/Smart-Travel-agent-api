"""
Resolve stored image values to absolute URLs for API responses.
"""

from django.conf import settings


def _site_base_url() -> str:
    return (getattr(settings, 'SITE_BASE_URL', None) or '').rstrip('/')


def _s3_configured() -> bool:
    return bool(
        getattr(settings, 'USE_S3', False)
        and getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    )


def _s3_url_for_key(key: str) -> str:
    key = key.lstrip('/')
    media_url = getattr(settings, 'MEDIA_URL', '').rstrip('/')
    if media_url:
        return f'{media_url}/{key}'
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    region = getattr(settings, 'AWS_S3_REGION_NAME', 'eu-north-1')
    return f'https://{bucket}.s3.{region}.amazonaws.com/{key}'


def resolve_media_url(image_value) -> str:
    """
    Turn a stored image path/URL into a browser-ready absolute URL.

    Supports S3 HTTPS URLs, legacy /media/ paths, and Cloudinary URLs.
    """
    if not image_value:
        return ''

    raw = str(image_value).strip()
    if not raw:
        return ''

    if raw.startswith('https://'):
        return raw
    if raw.startswith('http://'):
        return raw.replace('http://', 'https://', 1)
    if raw.startswith('//'):
        return f'https:{raw}'

    url_str = raw
    if hasattr(image_value, 'url'):
        try:
            url_str = (image_value.url or raw).strip()
        except Exception:
            url_str = raw

    if url_str.startswith('https://') or url_str.startswith('http://'):
        return url_str.replace('http://', 'https://', 1) if url_str.startswith('http://') else url_str

    if 'amazonaws.com' in url_str or 's3.' in url_str:
        if not url_str.startswith('http'):
            return f'https://{url_str.lstrip("/")}'
        return url_str

    if 'res.cloudinary.com' in url_str:
        if url_str.startswith('http'):
            return url_str.replace('http://', 'https://', 1)
        return f'https://{url_str.lstrip("/")}'

    if url_str.startswith('/media/'):
        base = _site_base_url()
        return f'{base}{url_str}' if base else url_str

    if '/media/' in url_str:
        idx = url_str.find('/media/')
        path = url_str[idx:]
        base = _site_base_url()
        return f'{base}{path}' if base else path

    if _s3_configured() and '://' not in url_str:
        return _s3_url_for_key(url_str)

    if url_str.startswith('/'):
        base = _site_base_url()
        return f'{base}{url_str}' if base else url_str

    return url_str
