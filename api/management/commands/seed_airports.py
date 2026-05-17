import csv
import os
from django.core.management.base import BaseCommand
from api.models import City

class Command(BaseCommand):
    help = 'Seeds airport data from a CSV file'

    def handle(self, *args, **options):
        csv_path = os.path.join(os.getcwd(), 'airports.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found at {csv_path}'))
            return

        self.stdout.write(self.style.SUCCESS('Starting airport seeding...'))
        
        count = 0
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                city_raw = row['city']
                country = row['country']
                code = row['code']
                
                # Simple logic to extract city name if it's "City, State"
                if ',' in city_raw:
                    name = city_raw.split(',')[0].strip()
                    airport_name = city_raw.strip()
                else:
                    name = city_raw.strip()
                    airport_name = f"{name} Airport"

                try:
                    city, created = City.objects.update_or_create(
                        iata_code=code.upper(),
                        defaults={
                            'name': name,
                            'country': country,
                            'airport_name': airport_name,
                            'is_active': True
                        }
                    )
                    if created:
                        count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Failed to seed {code}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} new airports!'))
