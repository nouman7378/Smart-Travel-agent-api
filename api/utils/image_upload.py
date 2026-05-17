"""
Local image upload utility.

Saves uploaded images to MEDIA_ROOT/<subfolder>/ and returns the URL path.
Replaces Cloudinary uploads with local file storage.
"""

import os
import uuid
import sys
from django.conf import settings


def save_uploaded_image(uploaded_file, subfolder='uploads'):
    """
    Save an uploaded file to the local media directory.

    Args:
        uploaded_file: Django UploadedFile (from request.FILES)
        subfolder: subdirectory inside MEDIA_ROOT (e.g. 'hotels', 'rooms', 'packages', 'cars')

    Returns:
        str: The relative URL path to the saved image (e.g. '/media/hotels/abc123.jpg')
             Returns '' if the save fails.
    """
    try:
        # Build the target directory
        upload_dir = os.path.join(settings.MEDIA_ROOT, subfolder)
        os.makedirs(upload_dir, exist_ok=True)

        # Generate a unique filename to prevent collisions
        ext = os.path.splitext(uploaded_file.name)[1].lower() or '.jpg'
        # Sanitize extension
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
        if ext not in allowed_extensions:
            ext = '.jpg'

        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, unique_name)

        # Write file to disk in chunks (memory-efficient for large files)
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Build the URL that the frontend will use
        image_url = f"{settings.MEDIA_URL}{subfolder}/{unique_name}"

        print(f"Image saved locally: {file_path} -> {image_url}", file=sys.stderr)
        return image_url

    except Exception as e:
        print(f"Local image save failed: {str(e)}", file=sys.stderr)
        return ''
