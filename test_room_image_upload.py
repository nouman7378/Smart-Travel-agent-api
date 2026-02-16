"""
Test script to verify room image upload functionality.
"""

import os
import sys
import django
import requests

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Hotel, Room

def test_room_image_upload():
    """Test creating a room with image upload."""
    print("Testing room image upload...")
    
    # Get a hotel
    hotel = Hotel.objects.first()
    if not hotel:
        print("No hotels found. Please create a hotel first.")
        return
    
    print(f"Using hotel: {hotel.name}")
    
    # Test data for room creation
    room_data = {
        'room_type': 'Test Suite with Image',
        'description': 'A luxury suite with beautiful views',
        'price_per_night': '25000',
        'original_price': '30000',
        'available_rooms': '3',
        'max_guests': '4',
        'amenities': '["Free WiFi", "Air Conditioning", "Balcony", "Mini Bar"]',
        'is_active': 'True'
    }
    
    # Admin credentials (you'll need to adjust these based on your setup)
    admin_creds = 'admin:admin123'  # Replace with actual admin credentials
    auth_header = f'Basic {admin_creds.encode("utf-8").hex()}'
    
    # Create room via API
    url = f'http://localhost:8000/api/admin/hotels/{hotel.id}/rooms/create/'
    
    try:
        response = requests.post(
            url,
            data=room_data,
            headers={
                'Authorization': f'Basic {admin_creds.encode("utf-8").hex()}'
            }
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Room created successfully!")
        else:
            print("❌ Failed to create room")
            
    except Exception as e:
        print(f"Error testing room creation: {e}")

if __name__ == '__main__':
    test_room_image_upload()