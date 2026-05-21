"""
Upload legacy /media/... images to S3 and update model fields with public URLs.

Run locally when MEDIA_ROOT still has the files:

    python manage.py migrate_local_images_to_s3
"""

import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from api.models import Car, Hotel, Package, Room


def _local_path_from_field(value: str) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if '/media/' in s:
        s = s[s.find('/media/') + len('/media/') :]
    elif s.startswith('media/'):
        s = s[len('media/') :]
    elif s.startswith('http'):
        return None
    else:
        return None
    full = settings.MEDIA_ROOT / s
    return str(full) if full.is_file() else None


class Command(BaseCommand):
    help = 'Upload local /media files to S3 and store HTTPS URLs on models.'

    def handle(self, *args, **options):
        if not getattr(settings, 'USE_S3', False):
            self.stderr.write('S3 is not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.')
            return

        jobs = [
            (Hotel, 'image', 'hotels'),
            (Room, 'room_image', 'rooms'),
            (Car, 'car_image', 'cars'),
            (Package, 'hotel_image', 'packages'),
        ]

        migrated = 0
        skipped = 0
        missing = 0

        for model, field_name, folder in jobs:
            for obj in model.objects.all():
                field_value = getattr(obj, field_name, '') or ''
                if not field_value:
                    skipped += 1
                    continue
                if str(field_value).startswith('http'):
                    skipped += 1
                    continue

                path = _local_path_from_field(field_value)
                if not path:
                    missing += 1
                    self.stdout.write(f'  No local file for {model.__name__} pk={obj.pk}')
                    continue

                try:
                    filename = os.path.basename(path)
                    key = f'{folder}/{filename}'
                    with open(path, 'rb') as f:
                        saved_key = default_storage.save(key, f)
                    url = default_storage.url(saved_key)
                    if url.startswith('http://'):
                        url = url.replace('http://', 'https://', 1)
                    setattr(obj, field_name, url)
                    obj.save(update_fields=[field_name])
                    migrated += 1
                    self.stdout.write(self.style.SUCCESS(f'  Migrated {model.__name__} pk={obj.pk} → {url}'))
                except Exception as exc:
                    self.stderr.write(f'  Failed {model.__name__} pk={obj.pk}: {exc}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. migrated={migrated} skipped={skipped} missing_file={missing}'
            )
        )
