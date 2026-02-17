"""
Test script to add sample packages for testing purposes.
Run this script to populate the database with sample package data.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Package

def create_sample_packages():
    """Create sample packages for testing."""
    print("Creating sample packages...")
    
    # Sample package data with PKR prices
    sample_packages = [
        {
            'title': 'Bali Paradise Escape',
            'destination': 'Bali, Indonesia',
            'description': 'Experience the exotic beauty of Bali with this 7-night luxury package. Enjoy pristine beaches, ancient temples, and world-class resorts.',
            'hotel_name': 'The Oberoi, Bali',
            'hotel_location': 'Seminyak Beach, Bali',
            'hotel_stars': 5,
            'hotel_rating': 4.8,
            'hotel_review_count': 2456,
            'hotel_image_url': 'https://images.unsplash.com/photo-1551786781-d3fee5d55364?w=800&q=80',
            'airline': 'PIA - Pakistan International Airlines',
            'departure_airport': 'ISB',
            'arrival_airport': 'DPS',
            'flight_duration': '6h 30m',
            'flight_stops': 1,
            'departure_time': '22:00',
            'arrival_time': '12:30',
            'price_per_person': 125000,
            'original_price': 165000,
            'nights': 7,
            'package_type': 'luxury',
            'highlights': ['beachfront', 'all_inclusive', 'free_wifi', 'spa_access'],
            'includes': ['Round trip flights', 'Hotel accommodation', 'Breakfast daily', 'Airport transfers', 'Spa voucher'],
            'availability': 50,
            'bookings': 12,
            'is_featured': True,
            'is_popular': True,
            'is_active': True,
            'status': 'active',
        },
        {
            'title': 'Dubai Luxury Shopping & Sightseeing',
            'destination': 'Dubai, UAE',
            'description': 'Indulge in luxury shopping, stunning architecture, and desert adventures in the vibrant city of Dubai.',
            'hotel_name': 'Burj Al Arab',
            'hotel_location': 'Jumeirah Beach, Dubai',
            'hotel_stars': 5,
            'hotel_rating': 4.9,
            'hotel_review_count': 3200,
            'hotel_image_url': 'https://images.unsplash.com/photo-1578922746465-78342604a0f1?w=800&q=80',
            'airline': 'Emirates',
            'departure_airport': 'ISB',
            'arrival_airport': 'DXB',
            'flight_duration': '3h 45m',
            'flight_stops': 0,
            'departure_time': '10:15',
            'arrival_time': '13:30',
            'price_per_person': 98000,
            'original_price': 145000,
            'nights': 5,
            'package_type': 'luxury',
            'highlights': ['city_center', 'free_wifi', 'gym_access', 'butler_service'],
            'includes': ['Round trip flights', 'Hotel accommodation', 'Airport transfers', 'Desert Safari tour'],
            'availability': 35,
            'bookings': 8,
            'is_featured': True,
            'is_popular': True,
            'is_active': True,
            'status': 'active',
        },
        {
            'title': 'London Historic & Cultural Tour',
            'destination': 'London, United Kingdom',
            'description': 'Explore the rich history and culture of London with guided tours of historic landmarks and museums.',
            'hotel_name': 'The Dorchester',
            'hotel_location': 'Mayfair, London',
            'hotel_stars': 5,
            'hotel_rating': 4.7,
            'hotel_review_count': 1890,
            'hotel_image_url': 'https://images.unsplash.com/photo-1512207736139-7c1fdd299c51?w=800&q=80',
            'airline': 'British Airways',
            'departure_airport': 'ISB',
            'arrival_airport': 'LHR',
            'flight_duration': '9h 15m',
            'flight_stops': 0,
            'departure_time': '23:45',
            'arrival_time': '11:30',
            'price_per_person': 156000,
            'original_price': 210000,
            'nights': 6,
            'package_type': 'cultural',
            'highlights': ['historic_area', 'museum_access', 'breakfast_included', 'free_wifi'],
            'includes': ['Round trip flights', 'Hotel accommodation', 'Breakfast daily', 'Museum tours', 'Theater show ticket'],
            'availability': 28,
            'bookings': 5,
            'is_featured': True,
            'is_popular': False,
            'is_active': True,
            'status': 'active',
        },
        {
            'title': 'Maldives Honeymoon Paradise',
            'destination': 'Maldives',
            'description': 'Perfect romantic getaway with overwater villas, pristine beaches, and world-class snorkeling in crystal-clear waters.',
            'hotel_name': 'Conrad Rangali Island',
            'hotel_location': 'North Ari Atoll, Maldives',
            'hotel_stars': 5,
            'hotel_rating': 4.9,
            'hotel_review_count': 1650,
            'hotel_image_url': 'https://images.unsplash.com/photo-1512207736139-7c1fdd299c51?w=800&q=80',
            'airline': 'SriLankan Airlines',
            'departure_airport': 'ISB',
            'arrival_airport': 'MLE',
            'flight_duration': '5h 20m',
            'flight_stops': 1,
            'departure_time': '01:30',
            'arrival_time': '08:45',
            'price_per_person': 185000,
            'original_price': 250000,
            'nights': 5,
            'package_type': 'romantic',
            'highlights': ['overwater_villa', 'snorkeling', 'private_beach', 'spa_access'],
            'includes': ['Round trip flights', 'Overwater villa accommodation', 'All meals', 'Spa treatments', 'Snorkeling equipment'],
            'availability': 15,
            'bookings': 3,
            'is_featured': True,
            'is_popular': True,
            'is_active': True,
            'status': 'active',
        },
        {
            'title': 'Greece Island Hopping Adventure',
            'destination': 'Greece',
            'description': 'Discover the stunning Greek islands with island hopping, ancient ruins, and Mediterranean cuisine.',
            'hotel_name': 'Hotel Grande Bretagne',
            'hotel_location': 'Syntagma Square, Athens',
            'hotel_stars': 4,
            'hotel_rating': 4.6,
            'hotel_review_count': 2100,
            'hotel_image_url': 'https://images.unsplash.com/photo-1566525577519-fafb02fad01f?w=800&q=80',
            'airline': 'Aegean Airlines',
            'departure_airport': 'ISB',
            'arrival_airport': 'ATH',
            'flight_duration': '8h 40m',
            'flight_stops': 1,
            'departure_time': '14:20',
            'arrival_time': '08:15',
            'price_per_person': 89000,
            'original_price': 125000,
            'nights': 8,
            'package_type': 'adventure',
            'highlights': ['breakfast_included', 'free_wifi', 'city_center', 'free_cancellation'],
            'includes': ['Round trip flights', 'Hotel accommodation', 'Breakfast daily', 'Island tours', 'Ferry passes'],
            'availability': 60,
            'bookings': 15,
            'is_featured': False,
            'is_popular': True,
            'is_active': True,
            'status': 'active',
        },
        {
            'title': 'Turkey Beach & History Combo',
            'destination': 'Istanbul & Cappadocia, Turkey',
            'description': 'Combine beach relaxation with historical exploration in this unique Turkish package.',
            'hotel_name': 'Four Seasons Hotel Sultanahmet',
            'hotel_location': 'Old City, Istanbul',
            'hotel_stars': 5,
            'hotel_rating': 4.8,
            'hotel_review_count': 1450,
            'hotel_image_url': 'https://images.unsplash.com/photo-1551501350-4091e0c38ba4?w=800&q=80',
            'airline': 'Turkish Airlines',
            'departure_airport': 'ISB',
            'arrival_airport': 'IST',
            'flight_duration': '6h 10m',
            'flight_stops': 0,
            'departure_time': '18:00',
            'arrival_time': '22:00',
            'price_per_person': 125000,
            'original_price': 175000,
            'nights': 7,
            'package_type': 'cultural',
            'highlights': ['free_cancellation', 'breakfast_included', 'city_center', 'historic_area'],
            'includes': ['Round trip flights', 'Hotel accommodation', 'Breakfast daily', 'Guided tours', 'Hot air balloon ride'],
            'availability': 42,
            'bookings': 10,
            'is_featured': False,
            'is_popular': True,
            'is_active': True,
            'status': 'active',
        },
    ]
    
    # Create packages
    for pkg_data in sample_packages:
        # Check if package already exists
        existing_pkg = Package.objects.filter(
            title=pkg_data['title'],
            destination=pkg_data['destination']
        ).first()
        
        if existing_pkg:
            print(f"  - Package '{pkg_data['title']}' already exists, updating...")
            for key, value in pkg_data.items():
                setattr(existing_pkg, key, value)
            existing_pkg.save()
        else:
            print(f"  - Creating package '{pkg_data['title']}'...")
            Package.objects.create(**pkg_data)
    
    print(f"\nSample packages created successfully!")
    print(f"Total packages: {Package.objects.count()}")

if __name__ == '__main__':
    create_sample_packages()
