from django.core.management.base import BaseCommand

from api.models import Hotel, KnowledgeDocument, Package


class Command(BaseCommand):
    help = "Seed demo travel data for Islamabad and Murree for AI/RAG testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding AI demo data..."))

        self._create_hotels()
        self._create_packages()
        self._create_knowledge_documents()

        self.stdout.write(self.style.SUCCESS("AI demo data seeding completed."))

    def _create_hotels(self) -> None:
        hotels = [
            {
                "name": "Islamabad Serenity Hotel",
                "location": "Islamabad, Pakistan",
                "address": "Blue Area, Islamabad",
                "stars": 4,
                "rating": 4.5,
                "review_count": 320,
                "distance_from_center": 1.2,
                "image_url": "https://res.cloudinary.com/demo/image/upload/v1730000000/islamabad-hotel.jpg",
            },
            {
                "name": "Murree Hills Resort",
                "location": "Murree, Pakistan",
                "address": "Mall Road, Murree",
                "stars": 3,
                "rating": 4.3,
                "review_count": 210,
                "distance_from_center": 0.5,
                "image_url": "https://res.cloudinary.com/demo/image/upload/v1730000000/murree-resort.jpg",
            },
        ]

        for data in hotels:
            obj, created = Hotel.objects.update_or_create(
                name=data["name"],
                location=data["location"],
                defaults=data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} hotel: {obj}")

    def _create_packages(self) -> None:
        packages = [
            {
                "title": "Islamabad City Escape",
                "destination": "Islamabad, Pakistan",
                "description": "3-night city break in Islamabad with guided tours of Faisal Mosque, Daman-e-Koh and Pakistan Monument.",
                "hotel_name": "Islamabad Serenity Hotel",
                "hotel_location": "Blue Area, Islamabad",
                "hotel_stars": 4,
                "hotel_rating": 4.5,
                "hotel_review_count": 320,
                "hotel_image_url": "https://res.cloudinary.com/demo/image/upload/v1730000000/islamabad-hotel.jpg",
                "airline": "PK Demo Air",
                "departure_airport": "ISB",
                "arrival_airport": "ISB",
                "flight_duration": "1h 0m",
                "flight_stops": 0,
                "departure_time": "09:00",
                "arrival_time": "10:00",
                "price_per_person": 35000,
                "original_price": 45000,
                "price_per_package": 70000,
                "nights": 3,
                "package_type": "city",
                "highlights": [
                    "city_center",
                    "free_cancellation",
                    "breakfast_included",
                    "mountain_views",
                ],
                "includes": [
                    "3 nights accommodation with breakfast",
                    "Airport transfers",
                    "Guided city tour",
                ],
                "availability": 10,
                "bookings": 0,
                "is_featured": True,
                "is_popular": True,
                "is_active": True,
                "status": "active",
            },
            {
                "title": "Murree Hills Getaway",
                "destination": "Murree, Pakistan",
                "description": "2-night relaxing stay in the hills of Murree with chairlift experience and Mall Road walk.",
                "hotel_name": "Murree Hills Resort",
                "hotel_location": "Mall Road, Murree",
                "hotel_stars": 3,
                "hotel_rating": 4.3,
                "hotel_review_count": 210,
                "hotel_image_url": "https://res.cloudinary.com/demo/image/upload/v1730000000/murree-resort.jpg",
                "airline": "PK Demo Air",
                "departure_airport": "ISB",
                "arrival_airport": "MUR",
                "flight_duration": "0h 45m",
                "flight_stops": 0,
                "departure_time": "11:00",
                "arrival_time": "11:45",
                "price_per_person": 28000,
                "original_price": 36000,
                "price_per_package": 56000,
                "nights": 2,
                "package_type": "mountain",
                "highlights": [
                    "mountain_views",
                    "free_cancellation",
                    "breakfast_included",
                ],
                "includes": [
                    "2 nights accommodation with breakfast",
                    "Return transport from Islamabad",
                    "Chairlift tickets",
                ],
                "availability": 8,
                "bookings": 0,
                "is_featured": True,
                "is_popular": True,
                "is_active": True,
                "status": "active",
            },
        ]

        for data in packages:
            obj, created = Package.objects.update_or_create(
                title=data["title"],
                destination=data["destination"],
                defaults=data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} package: {obj}")

    def _create_knowledge_documents(self) -> None:
        docs = [
            {
                "title": "Best time to visit Islamabad",
                "destination": "Islamabad",
                "category": "weather",
                "content": (
                    "Islamabad is pleasant in spring (March–April) and autumn (September–November) "
                    "with mild temperatures and clear views of the Margalla Hills. Summers can be "
                    "hot during the day, while winters are cool with occasional rain."
                ),
                "tags": ["islamabad", "weather", "best_time"],
                "source": "internal_guide",
            },
            {
                "title": "Top attractions in Murree",
                "destination": "Murree",
                "category": "guide",
                "content": (
                    "Key attractions in Murree include Mall Road, Pindi Point chairlift, Patriata "
                    "(New Murree), Kashmir Point, and various viewpoints offering panoramic hill "
                    "views. Weekdays are generally less crowded than weekends."
                ),
                "tags": ["murree", "things_to_do", "family"],
                "source": "internal_guide",
            },
        ]

        for data in docs:
            obj, created = KnowledgeDocument.objects.update_or_create(
                title=data["title"],
                destination=data["destination"],
                defaults=data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} knowledge document: {obj}")

