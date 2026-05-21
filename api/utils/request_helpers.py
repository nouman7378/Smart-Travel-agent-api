"""Helpers for detecting request content types."""


def is_multipart_form_request(request) -> bool:
    """True when the request carries form fields and/or uploaded files."""
    if request.FILES:
        return True
    content_type = (request.content_type or '').lower()
    if 'multipart/form-data' in content_type:
        return True
    # FormData from admin UI may omit content-type in edge cases; POST fields imply form submit
    if request.POST and request.method == 'POST':
        return True
    return False
