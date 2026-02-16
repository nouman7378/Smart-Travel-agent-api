"""
Test script to add sample rooms to hotels for testing purposes.
Run this script to populate the database with sample room data.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Hotel, Room

def create_sample_rooms():
    """Create sample rooms for testing."""
    print("Creating sample rooms...")
    
    # Get all hotels
    hotels = Hotel.objects.all()
    
    if not hotels.exists():
        print("No hotels found. Please create some hotels first.")
        return
    
    # Sample room data
    sample_rooms = [
        {
            'room_type': 'Deluxe Room',
            'description': 'Spacious room with city view, king bed, and modern amenities',
            'price_per_night': 15000,
            'original_price': 18000,
            'available_rooms': 10,
            'max_guests': 2,
            'amenities': ['Free WiFi', 'Air Conditioning', 'TV', 'Mini Bar'],
        },
        {
            'room_type': 'Executive Suite',
            'description': 'Luxury suite with separate living area and premium amenities',
            'price_per_night': 25000,
            'original_price': 30000,
            'available_rooms': 5,
            'max_guests': 4,
            'amenities': ['Free WiFi', 'Air Conditioning', 'TV', 'Mini Bar', 'Balcony'],
        },
        {
            'room_type': 'Presidential Suite',
            'description': 'Ultimate luxury with panoramic views and butler service',
            'price_per_night': 50000,
            'available_rooms': 2,
            'max_guests': 6,
            'amenities': ['Free WiFi', 'Air Conditioning', 'TV', 'Mini Bar', 'Balcony', 'Jacuzzi'],
        },
        {
            'room_type': 'Standard Room',
            'description': 'Comfortable room with essential amenities',
            'price_per_night': 8000,
            'available_rooms': 15,
            'max_guests': 2,
            'amenities': ['Free WiFi', 'Air Conditioning', 'TV'],
        },
    ]
    
    # Create rooms for each hotel
    for hotel in hotels:
        print(f"Creating rooms for {hotel.name}...")
        
        for room_data in sample_rooms:
            # Check if room already exists
            existing_room = Room.objects.filter(
                hotel=hotel,
                room_type=room_data['room_type']
            ).first()
            
            if existing_room:
                print(f"  - Room '{room_data['room_type']}' already exists, updating...")
                existing_room.price_per_night = room_data['price_per_night']
                existing_room.original_price = room_data['original_price']
                existing_room.available_rooms = room_data['available_rooms']
                existing_room.save()
            else:
                print(f"  - Creating room '{room_data['room_type']}'...")
                Room.objects.create(
                    hotel=hotel,
                    **room_data
                )
    
    print(f"\nSample rooms created successfully!")
    print(f"Total hotels: {hotels.count()}")
    print(f"Total rooms: {Room.objects.count()}")

if __name__ == '__main__':
    create_sample_rooms()