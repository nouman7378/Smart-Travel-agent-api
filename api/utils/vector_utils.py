from api.models import Hotel, Room, Package, Car, KnowledgeDocument

def get_document_id(instance):
    """Generate a unique ID for the vector store."""
    return f"{instance.__class__.__name__}_{instance.pk}"

def format_hotel_for_vector(hotel: Hotel) -> str:
    return f"Hotel: {hotel.name}\nLocation: {hotel.location}\nAddress: {hotel.address}\nStars: {hotel.stars}\nRating: {hotel.rating}/5 ({hotel.review_count} reviews)\nDistance from center: {hotel.distance_from_center}km"

def format_room_for_vector(room: Room) -> str:
    amenities = ", ".join(room.amenities) if room.amenities else "standard amenities"
    return f"Room: {room.room_type} at {room.hotel.name} ({room.hotel.location})\nPrice: PKR {room.price_per_night}\nMax Guests: {room.max_guests}\nAmenities: {amenities}\nDescription: {room.description}"

def format_package_for_vector(package: Package) -> str:
    includes = ", ".join(package.includes) if package.includes else "standard inclusions"
    highlights = ", ".join(package.highlights) if package.highlights else ""
    return f"Travel Package: {package.title}\nDestination: {package.destination}\nDuration: {package.nights} nights\nPrice per person: PKR {package.price_per_person}\nHotel: {package.hotel_name} ({package.hotel_stars} stars)\nIncludes: {includes}\nHighlights: {highlights}\nDescription: {package.description}"

def format_car_for_vector(car: Car) -> str:
    features = ", ".join(car.features) if car.features else "standard features"
    return f"Rental Car: {car.company} {car.model}\nType: {car.type}\nTransmission: {car.transmission}\nFuel: {car.fuel_type}\nSeats: {car.seats}\nPrice per day: PKR {car.price_per_day}\nFeatures: {features}"

def format_knowledge_doc_for_vector(doc: KnowledgeDocument) -> str:
    tags = ", ".join(doc.tags) if doc.tags else ""
    return f"Travel Guide/Tip: {doc.title}\nDestination: {doc.destination}\nCategory: {doc.category}\nContent: {doc.content}\nTags: {tags}"

def get_vector_text(instance) -> str:
    if isinstance(instance, Hotel):
        return format_hotel_for_vector(instance)
    elif isinstance(instance, Room):
        return format_room_for_vector(instance)
    elif isinstance(instance, Package):
        return format_package_for_vector(instance)
    elif isinstance(instance, Car):
        return format_car_for_vector(instance)
    elif isinstance(instance, KnowledgeDocument):
        return format_knowledge_doc_for_vector(instance)
    return ""

def get_vector_metadata(instance) -> dict:
    is_active = getattr(instance, 'is_active', getattr(instance, 'is_available', True))
    return {
        "type": instance.__class__.__name__,
        "model_id": instance.pk,
        "is_active": is_active
    }
