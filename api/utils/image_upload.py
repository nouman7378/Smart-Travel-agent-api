"""
Cloudinary image upload utility.

Saves uploaded images to Cloudinary and returns the secure URL path.
"""

import sys
import cloudinary.uploader


def save_uploaded_image(uploaded_file, subfolder='uploads'):
    """
    Save an uploaded file to Cloudinary.

    Args:
        uploaded_file: Django UploadedFile (from request.FILES)
        subfolder: subdirectory/folder inside Cloudinary (e.g. 'hotels', 'rooms', 'packages', 'cars')

    Returns:
        str: The full secure Cloudinary URL.
             Returns '' if the upload fails.
    """
    try:
        # Upload directly to Cloudinary
        result = cloudinary.uploader.upload(
            uploaded_file,
            folder=subfolder
        )
        url = result.get('secure_url', '')
        print(f"Image uploaded to Cloudinary: {url}", file=sys.stderr)
        return url
    except Exception as e:
        print(f"Cloudinary upload failed: {str(e)}", file=sys.stderr)
        return ''
