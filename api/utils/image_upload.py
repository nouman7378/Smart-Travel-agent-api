"""
Cloudinary image upload utility.

Saves uploaded images to Cloudinary and returns the secure URL path.
Falls back to local file storage if Cloudinary upload fails.
"""

import os
import sys
import uuid
import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def save_uploaded_image(uploaded_file, subfolder='uploads'):
    """
    Save an uploaded file to Cloudinary with a local storage fallback.

    Args:
        uploaded_file: Django UploadedFile (from request.FILES)
        subfolder: subdirectory/folder (e.g. 'hotels', 'rooms', 'packages', 'cars')

    Returns:
        str: The full secure Cloudinary URL or local relative media path.
             Returns '' if both upload and local save fail.
    """
    # 1. Attempt Cloudinary Upload
    try:
        # Explicitly configure cloudinary SDK using settings dictionary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', ''),
            api_key=settings.CLOUDINARY_STORAGE.get('API_KEY', ''),
            api_secret=settings.CLOUDINARY_STORAGE.get('API_SECRET', ''),
            secure=True
        )
        
        result = cloudinary.uploader.upload(
            uploaded_file,
            folder=subfolder
        )
        url = result.get('secure_url', '')
        if url:
            print(f"Image uploaded to Cloudinary: {url}", file=sys.stderr)
            return url
    except Exception as e:
        print(f"Cloudinary upload failed: {str(e)}. Falling back to local storage...", file=sys.stderr)

    # 2. Local Storage Fallback
    try:
        fs = FileSystemStorage()
        ext = os.path.splitext(uploaded_file.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(subfolder, filename)
        
        saved_name = fs.save(filepath, uploaded_file)
        local_url = fs.url(saved_name)
        print(f"Image saved locally: {local_url}", file=sys.stderr)
        return local_url
    except Exception as local_err:
        print(f"Local storage fallback also failed: {str(local_err)}", file=sys.stderr)
        return ''
