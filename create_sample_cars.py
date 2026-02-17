"""
Test script to add sample cars for testing purposes.
Run this script to populate the database with sample car data.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Car

def create_sample_cars():
    """Create sample cars for testing."""
    print("Creating sample cars...")
    
    # Sample car data with PKR prices
    sample_cars = [
        {
            'model': 'Toyota Camry',
            'type': 'mid-size',
            'company': 'Hertz',
            'price_per_day': 4500,
            'original_price': 6000,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 2,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.5,
            'review_count': 234,
            'features': ['GPS', 'Bluetooth', 'USB Charger', 'Backup Camera'],
            'is_available': True,
        },
        {
            'model': 'BMW 3 Series',
            'type': 'luxury',
            'company': 'Avis',
            'price_per_day': 8900,
            'original_price': 12000,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 2,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.8,
            'review_count': 456,
            'features': ['GPS', 'Leather Seats', 'Sunroof', 'Premium Sound'],
            'is_available': True,
        },
        {
            'model': 'Honda Civic',
            'type': 'compact',
            'company': 'Enterprise',
            'price_per_day': 3500,
            'original_price': 4500,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 1,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.6,
            'review_count': 189,
            'features': ['GPS', 'Bluetooth', 'USB Charger'],
            'is_available': True,
        },
        {
            'model': 'Ford Explorer',
            'type': 'suv',
            'company': 'Budget',
            'price_per_day': 7500,
            'original_price': 9500,
            'transmission': 'automatic',
            'seats': 7,
            'luggage_capacity': 4,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.4,
            'review_count': 312,
            'features': ['GPS', 'Third Row Seating', 'AWD', 'Roof Rack'],
            'is_available': True,
        },
        {
            'model': 'Mercedes-Benz E-Class',
            'type': 'luxury',
            'company': 'National',
            'price_per_day': 12000,
            'original_price': 15000,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 3,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.9,
            'review_count': 278,
            'features': ['GPS', 'Leather Seats', 'Sunroof', 'Premium Sound', 'Heated Seats'],
            'is_available': True,
        },
        {
            'model': 'Nissan Altima',
            'type': 'mid-size',
            'company': 'Alamo',
            'price_per_day': 4200,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 2,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.3,
            'review_count': 156,
            'features': ['GPS', 'Bluetooth', 'USB Charger'],
            'is_available': True,
        },
        {
            'model': 'Jeep Wrangler',
            'type': 'suv',
            'company': 'Thrifty',
            'price_per_day': 6800,
            'original_price': 8500,
            'transmission': 'manual',
            'seats': 5,
            'luggage_capacity': 2,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.7,
            'review_count': 421,
            'features': ['GPS', '4WD', 'Removable Doors', 'Roof Rack'],
            'is_available': True,
        },
        {
            'model': 'Tesla Model 3',
            'type': 'electric',
            'company': 'Hertz',
            'price_per_day': 9500,
            'original_price': 12500,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 2,
            'fuel_type': 'electric',
            'mileage': 'Unlimited',
            'rating': 4.9,
            'review_count': 567,
            'features': ['GPS', 'Autopilot', 'Supercharging', 'Premium Sound'],
            'is_available': True,
        },
        {
            'model': 'Chevrolet Malibu',
            'type': 'mid-size',
            'company': 'Enterprise',
            'price_per_day': 3800,
            'transmission': 'automatic',
            'seats': 5,
            'luggage_capacity': 2,
            'fuel_type': 'gasoline',
            'mileage': 'Unlimited',
            'rating': 4.2,
            'review_count': 198,
            'features': ['GPS', 'Bluetooth', 'USB Charger'],
            'is_available': True,
        },
    ]
    
    # Create cars
    for car_data in sample_cars:
        # Check if car already exists
        existing_car = Car.objects.filter(
            model=car_data['model'],
            company=car_data['company']
        ).first()
        
        if existing_car:
            print(f"  - Car '{car_data['model']}' already exists, updating...")
            for key, value in car_data.items():
                setattr(existing_car, key, value)
            existing_car.save()
        else:
            print(f"  - Creating car '{car_data['model']}'...")
            Car.objects.create(**car_data)
    
    print(f"\nSample cars created successfully!")
    print(f"Total cars: {Car.objects.count()}")

if __name__ == '__main__':
    create_sample_cars()