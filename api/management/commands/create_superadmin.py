"""
Management command to create the superadmin user.
Usage: python manage.py create_superadmin
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

SUPERADMIN_EMAIL = 'admin@admin.com'
SUPERADMIN_PASSWORD = 'admin123'


class Command(BaseCommand):
    help = 'Creates the superadmin user (admin@admin.com / admin123) with access to admin only.'

    def handle(self, *args, **options):
        if User.objects.filter(username=SUPERADMIN_EMAIL).exists():
            self.stdout.write(
                self.style.WARNING(f'Superadmin "{SUPERADMIN_EMAIL}" already exists. Skipping.')
            )
            return

        user = User.objects.create_superuser(
            username=SUPERADMIN_EMAIL,
            email=SUPERADMIN_EMAIL,
            password=SUPERADMIN_PASSWORD,
            first_name='Super',
            last_name='Admin',
        )
        self.stdout.write(
            self.style.SUCCESS(f'Superadmin created: {SUPERADMIN_EMAIL}')
        )
