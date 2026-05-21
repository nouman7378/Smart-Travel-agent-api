"""
Resolve stored image values to absolute URLs for API responses.

Private S3 buckets: returns time-limited presigned URLs so images load in the browser
without a public bucket policy.
"""

from django.conf import settings

# 7 days — long enough for admin sessions and catalog browsing
PRESIGNED_URL_EXPIRY = 604800


def _site_base_url() -> str:
    return (getattr(settings, 'SITE_BASE_URL', None) or '').rstrip('/')


def _s3_configured() -> bool:
    return bool(
        getattr(settings, 'USE_S3', False)
        and getattr(settings, 'AWS_ACCESS_KEY_ID', '')
        and getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    )


def _extract_s3_key(url: str) -> str | None:
    """Extract object key from a full S3 URL or a bare key like cars/abc.jpg."""
    url = (url or '').strip()
    if not url:
        return None
    if 'amazonaws.com/' in url:
        return url.split('amazonaws.com/', 1)[1].split('?')[0].lstrip('/')
    if '://' not in url and not url.startswith('/'):
        return url.lstrip('/')
    return None


def _presigned_s3_url(key: str) -> str:
    import boto3

    region = getattr(settings, 'AWS_S3_REGION_NAME', 'eu-north-1')
    client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=region,
        endpoint_url=f'https://s3.{region}.amazonaws.com',
    )
    return client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': key,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRY,
    )


def _maybe_presign_s3_url(url: str) -> str:
    if not url or not _s3_configured():
        return url
    if 'amazonaws.com' not in url and '://' not in url:
        key = _extract_s3_key(url)
        if key:
            try:
                return _presigned_s3_url(key)
            except Exception:
                pass
        return url
    key = _extract_s3_key(url)
    if not key:
        return url
    try:
        return _presigned_s3_url(key)
    except Exception:
        return url


def _s3_url_for_key(key: str) -> str:
    key = key.lstrip('/')
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    region = getattr(settings, 'AWS_S3_REGION_NAME', 'eu-north-1')
    return f'https://{bucket}.s3.{region}.amazonaws.com/{key}'


def resolve_media_url(image_value) -> str:
    """
    Turn a stored image path/URL into a browser-ready absolute URL.
    """
    if not image_value:
        return ''

    raw = str(image_value).strip()
    if not raw:
        return ''

    url_str = raw
    if hasattr(image_value, 'url'):
        try:
            url_str = (image_value.url or raw).strip()
        except Exception:
            url_str = raw

    if url_str.startswith('//'):
        url_str = f'https:{url_str}'
    elif url_str.startswith('http://'):
        url_str = url_str.replace('http://', 'https://', 1)

    if url_str.startswith('https://'):
        if 'res.cloudinary.com' in url_str:
            return url_str
        if 'amazonaws.com' in url_str:
            return _maybe_presign_s3_url(url_str)
        return url_str

    if 'res.cloudinary.com' in url_str:
        return f'https://{url_str.lstrip("/")}'

    if url_str.startswith('/media/'):
        base = _site_base_url()
        resolved = f'{base}{url_str}' if base else url_str
        return resolved

    if '/media/' in url_str:
        idx = url_str.find('/media/')
        path = url_str[idx:]
        base = _site_base_url()
        return f'{base}{path}' if base else path

    if _s3_configured() and '://' not in url_str:
        return _maybe_presign_s3_url(_s3_url_for_key(url_str))

    if url_str.startswith('/'):
        base = _site_base_url()
        return f'{base}{url_str}' if base else url_str

    return _maybe_presign_s3_url(url_str)
