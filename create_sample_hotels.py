"""
Test script to add sample hotels for testing purposes.
Run this script to populate the database with sample hotel data.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Hotel

def create_sample_hotels():
    """Create sample hotels for testing."""
    print("Creating sample hotels...")
    
    sample_hotels = [
        {
            'name': 'Islamabad Serena Hotel',
            'location': 'Islamabad, Pakistan',
            'address': 'Khayaban-e-Suhrawardy, Islamabad',
            'stars': 5,
            'rating': 4.8,
            'review_count': 1420,
            'distance_from_center': 3.5,
            'image_url': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80',
            'is_active': True,
        },
        {
            'name': 'Pearl Continental Lahore',
            'location': 'Lahore, Pakistan',
            'address': 'Mall Road, Lahore',
            'stars': 5,
            'rating': 4.7,
            'review_count': 2310,
            'distance_from_center': 1.2,
            'image_url': 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800&q=80',
            'is_active': True,
        },
        {
            'name': 'Marriott Islamabad',
            'location': 'Islamabad, Pakistan',
            'address': 'Aga Khan Road, Sector G-5, Islamabad',
            'stars': 5,
            'rating': 4.6,
            'review_count': 1890,
            'distance_from_center': 4.0,
            'image_url': 'https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800&q=80',
            'is_active': True,
        },
        {
            'name': 'Avari Towers Karachi',
            'location': 'Karachi, Pakistan',
            'address': 'Fatima Jinnah Road, Karachi',
            'stars': 4,
            'rating': 4.5,
            'review_count': 1650,
            'distance_from_center': 0.8,
            'image_url': 'https://images.unsplash.com/photo-1568495248636-6432b97bd949?w=800&q=80',
            'is_active': True,
        }
    ]
    
    for hotel_data in sample_hotels:
        existing_hotel = Hotel.objects.filter(name=hotel_data['name']).first()
        if existing_hotel:
            print(f"  - Hotel '{hotel_data['name']}' already exists, updating...")
            for key, value in hotel_data.items():
                setattr(existing_hotel, key, value)
            existing_hotel.save()
        else:
            print(f"  - Creating hotel '{hotel_data['name']}'...")
            Hotel.objects.create(**hotel_data)
            
    print(f"\nSample hotels created successfully! Total hotels: {Hotel.objects.count()}")

if __name__ == '__main__':
    create_sample_hotels()
