import json
from django.core.management.base import BaseCommand
from api.models import Package

class Command(BaseCommand):
    help = 'Populate database with sample package data'

    def handle(self, *args, **options):
        # Sample package data
        sample_packages = [
            {
                'title': '7-Day Dubai Luxury Getaway',
                'destination': 'Dubai, UAE',
                'description': 'Experience the luxury of Dubai with 5-star accommodation at Burj Al Arab and premium Emirates flights. Includes desert safari, city tours, and access to world-class attractions.',
                'hotel_name': 'Burj Al Arab Jumeirah',
                'hotel_location': 'Jumeirah Beach Road, Dubai',
                'hotel_stars': 5,
                'hotel_rating': 4.8,
                'hotel_review_count': 1250,
                'hotel_image_url': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800',
                'airline': 'Emirates',
                'departure_airport': 'ISB',
                'arrival_airport': 'DXB',
                'flight_duration': '4h 30m',
                'flight_stops': 0,
                'departure_time': '08:30',
                'arrival_time': '13:00',
                'price_per_person': 185000,
                'original_price': 220000,
                'price_per_package': 370000,
                'nights': 6,
                'package_type': 'luxury',
                'highlights': ['Luxury 5-star accommodation', 'Business class flights', 'Desert safari experience', 'Dubai Marina cruise', 'Mall of Emirates shopping'],
                'includes': ['Airport transfers', 'Daily breakfast', 'Desert safari with dinner', 'City tour', 'Mall of Emirates visit'],
                'availability': 15,
                'is_featured': True,
                'is_popular': True,
                'status': 'active'
            },
            {
                'title': '5-Day Turkey Cultural Tour',
                'destination': 'Istanbul, Turkey',
                'description': 'Discover the rich history and culture of Istanbul with comfortable 4-star accommodation and economy flights. Explore ancient mosques, historic sites, and vibrant markets.',
                'hotel_name': 'Hilton Istanbul Bosphorus',
                'hotel_location': 'Gümüssuyu Mah. Inönü Cad. No.8, Istanbul',
                'hotel_stars': 4,
                'hotel_rating': 4.5,
                'hotel_review_count': 890,
                'hotel_image_url': 'https://images.unsplash.com/photo-1590317387579-605b0c5501f9?w=800',
                'airline': 'Turkish Airlines',
                'departure_airport': 'ISB',
                'arrival_airport': 'IST',
                'flight_duration': '5h 15m',
                'flight_stops': 0,
                'departure_time': '10:15',
                'arrival_time': '15:30',
                'price_per_person': 95000,
                'original_price': 115000,
                'price_per_package': 190000,
                'nights': 4,
                'package_type': 'cultural',
                'highlights': ['4-star accommodation', 'Economy flights', 'Bosphorus cruise', 'Hagia Sophia visit', 'Grand Bazaar shopping'],
                'includes': ['Airport transfers', 'Daily breakfast', 'Bosphorus cruise', 'City tour', 'Hagia Sophia entry'],
                'availability': 25,
                'is_featured': False,
                'is_popular': True,
                'status': 'active'
            },
            {
                'title': '3-Day Bangkok Weekend Escape',
                'destination': 'Bangkok, Thailand',
                'description': 'Perfect weekend getaway to Bangkok with 4-star accommodation and budget-friendly flights. Experience Thai culture, street food, and vibrant nightlife.',
                'hotel_name': 'Novotel Bangkok Sukhumvit 20',
                'hotel_location': '20 Sukhumvit Soi 20, Bangkok',
                'hotel_stars': 4,
                'hotel_rating': 4.3,
                'hotel_review_count': 650,
                'hotel_image_url': 'https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=800',
                'airline': 'Thai Airways',
                'departure_airport': 'ISB',
                'arrival_airport': 'BKK',
                'flight_duration': '4h 45m',
                'flight_stops': 0,
                'departure_time': '14:20',
                'arrival_time': '21:05',
                'price_per_person': 45000,
                'original_price': 55000,
                'price_per_package': 90000,
                'nights': 2,
                'package_type': 'city',
                'highlights': ['4-star accommodation', 'Economy flights', 'Floating market tour', 'Temple visits', 'Street food experience'],
                'includes': ['Airport transfers', 'Daily breakfast', 'Floating market tour', 'Temple tour', 'City guide'],
                'availability': 30,
                'is_featured': False,
                'is_popular': False,
                'status': 'active'
            },
            {
                'title': '10-Day European Adventure',
                'destination': 'Paris, France',
                'description': 'Ultimate European experience visiting Paris, Rome, and Barcelona with luxury 5-star accommodations and premium flights. Includes guided tours and exclusive experiences.',
                'hotel_name': 'Le Meurice Paris',
                'hotel_location': '228 Rue de Rivoli, Paris',
                'hotel_stars': 5,
                'hotel_rating': 4.9,
                'hotel_review_count': 2100,
                'hotel_image_url': 'https://images.unsplash.com/photo-1502602898536-94319631b6d3?w=800',
                'airline': 'Air France',
                'departure_airport': 'ISB',
                'arrival_airport': 'CDG',
                'flight_duration': '7h 15m',
                'flight_stops': 0,
                'departure_time': '01:45',
                'arrival_time': '09:00',
                'price_per_person': 350000,
                'original_price': 420000,
                'price_per_package': 700000,
                'nights': 9,
                'package_type': 'luxury',
                'highlights': ['5-star luxury accommodation', 'Business class flights', 'Eiffel Tower experience', 'Louvre Museum tour', 'Seine River cruise'],
                'includes': ['Airport transfers', 'Daily breakfast', 'City tours', 'Museum entries', 'River cruise', 'Concierge service'],
                'availability': 8,
                'is_featured': True,
                'is_popular': True,
                'status': 'active'
            },
            {
                'title': '4-Day Maldives Paradise',
                'destination': 'Malé, Maldives',
                'description': 'Romantic getaway to the Maldives with overwater villa accommodation and scenic seaplane transfers. Perfect for honeymooners and couples seeking tranquility.',
                'hotel_name': 'Conrad Maldives Rangali Island',
                'hotel_location': 'Rangali Island, Malé',
                'hotel_stars': 5,
                'hotel_rating': 4.7,
                'hotel_review_count': 1560,
                'hotel_image_url': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800',
                'airline': 'Maldivian',
                'departure_airport': 'ISB',
                'arrival_airport': 'MLE',
                'flight_duration': '3h 20m',
                'flight_stops': 0,
                'departure_time': '11:30',
                'arrival_time': '14:50',
                'price_per_person': 125000,
                'original_price': 150000,
                'price_per_package': 250000,
                'nights': 3,
                'package_type': 'romantic',
                'highlights': ['Overwater villa accommodation', 'Seaplane transfers', 'Snorkeling adventures', 'Spa treatments', 'Sunset cruises'],
                'includes': ['Airport transfers', 'Daily breakfast', 'Snorkeling equipment', 'Sunset cruise', 'Spa treatment'],
                'availability': 12,
                'is_featured': True,
                'is_popular': True,
                'status': 'active'
            }
        ]

        # Create packages
        created_count = 0
        for package_data in sample_packages:
            # Check if package already exists
            if not Package.objects.filter(title=package_data['title']).exists():
                Package.objects.create(**package_data)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created package: {package_data["title"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Package already exists: {package_data["title"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample packages')
        )