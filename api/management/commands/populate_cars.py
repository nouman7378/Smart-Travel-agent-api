import json
from django.core.management.base import BaseCommand
from api.models import Car

class Command(BaseCommand):
    help = 'Populate database with sample car data'

    def handle(self, *args, **options):
        # Sample car data
        sample_cars = [
            {
                'model': 'Toyota Camry',
                'type': 'mid-size',
                'company': 'Hertz',
                'price_per_day': 4500,
                'original_price': 5500,
                'car_image_url': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=800',
                'transmission': 'automatic',
                'seats': 5,
                'luggage_capacity': 2,
                'fuel_type': 'gasoline',
                'mileage': 'Unlimited',
                'rating': 4.5,
                'review_count': 127,
                'features': ['GPS Navigation', 'Bluetooth', 'Backup Camera', 'USB Ports'],
                'is_available': True
            },
            {
                'model': 'Honda Civic',
                'type': 'compact',
                'company': 'Avis',
                'price_per_day': 3500,
                'original_price': 4200,
                'car_image_url': 'https://images.unsplash.com/photo-1542362567-b07e54358753?w=800',
                'transmission': 'automatic',
                'seats': 5,
                'luggage_capacity': 1,
                'fuel_type': 'gasoline',
                'mileage': '200 km/day',
                'rating': 4.3,
                'review_count': 89,
                'features': ['Air Conditioning', 'Bluetooth', 'FM Radio'],
                'is_available': True
            },
            {
                'model': 'BMW X5',
                'type': 'suv',
                'company': 'Enterprise',
                'price_per_day': 8500,
                'original_price': 10500,
                'car_image_url': 'https://images.unsplash.com/photo-1553440569-bcc63803a83d?w=800',
                'transmission': 'automatic',
                'seats': 7,
                'luggage_capacity': 4,
                'fuel_type': 'gasoline',
                'mileage': 'Unlimited',
                'rating': 4.8,
                'review_count': 203,
                'features': ['Leather Seats', 'Sunroof', 'GPS Navigation', 'Heated Seats', 'Premium Sound'],
                'is_available': True
            },
            {
                'model': 'Tesla Model 3',
                'type': 'electric',
                'company': 'Budget',
                'price_per_day': 6500,
                'original_price': 7800,
                'car_image_url': 'https://images.unsplash.com/photo-1594678372605-9102011c1240?w=800',
                'transmission': 'automatic',
                'seats': 5,
                'luggage_capacity': 2,
                'fuel_type': 'electric',
                'mileage': '300 km/day',
                'rating': 4.7,
                'review_count': 156,
                'features': ['Autopilot', 'Touchscreen Display', 'Fast Charging', 'Premium Interior'],
                'is_available': True
            },
            {
                'model': 'Ford Mustang',
                'type': 'convertible',
                'company': 'Alamo',
                'price_per_day': 7500,
                'original_price': 9000,
                'car_image_url': 'https://images.unsplash.com/photo-1591744905633-75fc8f33c950?w=800',
                'transmission': 'automatic',
                'seats': 4,
                'luggage_capacity': 1,
                'fuel_type': 'gasoline',
                'mileage': '250 km/day',
                'rating': 4.6,
                'review_count': 94,
                'features': ['Convertible Top', 'Sport Mode', 'Performance Tires', 'Custom Exhaust'],
                'is_available': True
            },
            {
                'model': 'Mercedes-Benz E-Class',
                'type': 'luxury',
                'company': 'Sixt',
                'price_per_day': 9500,
                'original_price': 11500,
                'car_image_url': 'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800',
                'transmission': 'automatic',
                'seats': 5,
                'luggage_capacity': 2,
                'fuel_type': 'gasoline',
                'mileage': 'Unlimited',
                'rating': 4.9,
                'review_count': 178,
                'features': ['Premium Leather', 'Massaging Seats', 'Advanced Safety', 'Ambient Lighting'],
                'is_available': True
            },
            {
                'model': 'Toyota Prius',
                'type': 'hybrid',
                'company': 'National',
                'price_per_day': 4000,
                'original_price': 4800,
                'car_image_url': 'https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=800',
                'transmission': 'automatic',
                'seats': 5,
                'luggage_capacity': 2,
                'fuel_type': 'hybrid',
                'mileage': 'Unlimited',
                'rating': 4.4,
                'review_count': 142,
                'features': ['Excellent Fuel Economy', 'Quiet Ride', 'Regenerative Braking'],
                'is_available': True
            },
            {
                'model': 'Chevrolet Silverado',
                'type': 'truck',
                'company': 'Thrifty',
                'price_per_day': 6000,
                'original_price': 7200,
                'car_image_url': 'https://images.unsplash.com/photo-1523676060187-f5fcab8b01f6?w=800',
                'transmission': 'automatic',
                'seats': 5,
                'luggage_capacity': 3,
                'fuel_type': 'diesel',
                'mileage': '300 km/day',
                'rating': 4.2,
                'review_count': 67,
                'features': ['Towing Package', '4WD Capability', 'Bed Liner', 'Tool Storage'],
                'is_available': True
            },
            {
                'model': 'Mercedes Sprinter',
                'type': 'van',
                'company': 'Dollar',
                'price_per_day': 5500,
                'original_price': 6600,
                'car_image_url': 'https://images.unsplash.com/photo-1561749800-4c1e4f1c6c7a?w=800',
                'transmission': 'automatic',
                'seats': 12,
                'luggage_capacity': 6,
                'fuel_type': 'diesel',
                'mileage': 'Unlimited',
                'rating': 4.1,
                'review_count': 53,
                'features': ['High Roof', 'Multiple Seating', 'Cargo Space', 'Commercial Grade'],
                'is_available': True
            }
        ]

        # Create cars
        created_count = 0
        for car_data in sample_cars:
            # Check if car already exists
            if not Car.objects.filter(model=car_data['model'], company=car_data['company']).exists():
                Car.objects.create(**car_data)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created car: {car_data["model"]} ({car_data["company"]})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Car already exists: {car_data["model"]} ({car_data["company"]})')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample cars')
        )