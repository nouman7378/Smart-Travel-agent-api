from django.db import models


class Hotel(models.Model):
    """
    Model to store hotel information.
    Managed by Super Admin and visible to users.
    """
    name = models.CharField(max_length=200, db_index=True)
    location = models.CharField(max_length=200)
    address = models.TextField()
    stars = models.IntegerField(choices=[(i, f'{i} Star') for i in range(1, 6)], default=3)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.IntegerField(default=0)
    distance_from_center = models.DecimalField(max_digits=6, decimal_places=2, help_text='Distance in kilometers')
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hotel'
        verbose_name_plural = 'Hotels'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name', 'location']),
            models.Index(fields=['stars', 'is_active']),
            models.Index(fields=['rating', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.stars}★) - {self.location}"

    @property
    def display_rating(self):
        """Returns formatted rating display."""
        return f"{self.rating:.1f}"

    @property
    def display_distance(self):
        """Returns formatted distance display."""
        return f"{self.distance_from_center:.1f} km from center"


class Room(models.Model):
    """
    Model to store room information for hotels.
    Managed by Super Admin.
    """
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100, help_text='e.g., Deluxe Room, Executive Suite')
    description = models.TextField(blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, help_text='Price in PKR')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Original price for discount display')
    available_rooms = models.IntegerField(default=0, help_text='Number of available rooms of this type')
    max_guests = models.IntegerField(default=2, help_text='Maximum number of guests allowed')
    room_image_url = models.URLField(max_length=500, blank=True, help_text='Optional room-specific image')
    amenities = models.JSONField(default=list, blank=True, help_text='List of amenities as strings')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'
        ordering = ['price_per_night']
        indexes = [
            models.Index(fields=['hotel', 'is_active']),
            models.Index(fields=['price_per_night']),
        ]

    def __str__(self):
        return f"{self.room_type} at {self.hotel.name}"

    @property
    def display_price(self):
        """Returns formatted price display."""
        return f"PKR {self.price_per_night:,.0f}"

    @property
    def display_original_price(self):
        """Returns formatted original price display."""
        if self.original_price:
            return f"PKR {self.original_price:,.0f}"
        return None

    @property
    def discount_percentage(self):
        """Calculate discount percentage if original price exists."""
        if self.original_price and self.original_price > self.price_per_night:
            return round(((self.original_price - self.price_per_night) / self.original_price) * 100)
        return 0


class City(models.Model):
    """
    Model to store cities and their airport information.
    Used for flight search autocomplete functionality.
    """
    name = models.CharField(max_length=100, db_index=True)
    iata_code = models.CharField(max_length=3, unique=True, db_index=True)
    airport_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100, db_index=True)
    country_code = models.CharField(max_length=2, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'
        ordering = ['name', 'iata_code']
        indexes = [
            models.Index(fields=['name', 'country']),
            models.Index(fields=['iata_code', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.iata_code}) - {self.airport_name}"

    @property
    def display_name(self):
        """Returns formatted display name for UI."""
        return f"{self.name} ({self.iata_code})"

    @property
    def full_display(self):
        """Returns full formatted display with airport and country."""
        return f"{self.name} ({self.iata_code}) - {self.airport_name}, {self.country}"


class Car(models.Model):
    """
    Model to store car information for rental.
    Managed by Super Admin.
    """
    CAR_TYPES = [
        ('compact', 'Compact'),
        ('mid-size', 'Mid-size'),
        ('suv', 'SUV'),
        ('luxury', 'Luxury'),
        ('electric', 'Electric'),
        ('convertible', 'Convertible'),
        ('truck', 'Truck'),
        ('van', 'Van'),
    ]
    
    TRANSMISSION_TYPES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ]
    
    FUEL_TYPES = [
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ]
    
    model = models.CharField(max_length=100, help_text='e.g., Toyota Camry, BMW 3 Series')
    type = models.CharField(max_length=20, choices=CAR_TYPES, help_text='Car type/category')
    company = models.CharField(max_length=100, help_text='Rental company name')
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, help_text='Price per day in PKR')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Original price for discount display')
    car_image_url = models.URLField(max_length=500, blank=True, help_text='Car image URL')
    transmission = models.CharField(max_length=10, choices=TRANSMISSION_TYPES, default='automatic')
    seats = models.IntegerField(default=5, help_text='Number of seats')
    luggage_capacity = models.IntegerField(default=2, help_text='Luggage capacity in bags')
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, default='gasoline')
    mileage = models.CharField(max_length=50, default='Unlimited', help_text='Mileage allowance')
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, help_text='Average customer rating')
    review_count = models.IntegerField(default=0, help_text='Number of customer reviews')
    features = models.JSONField(default=list, blank=True, help_text='List of features as strings')
    is_available = models.BooleanField(default=True, help_text='Is the car currently available for rent')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Car'
        verbose_name_plural = 'Cars'
        ordering = ['price_per_day']
        indexes = [
            models.Index(fields=['type', 'is_available']),
            models.Index(fields=['price_per_day']),
            models.Index(fields=['company', 'is_available']),
        ]

    def __str__(self):
        return f"{self.model} ({self.company})"

    @property
    def display_price(self):
        """Returns formatted price display."""
        return f"PKR {self.price_per_day:,.0f}"

    @property
    def display_original_price(self):
        """Returns formatted original price display."""
        if self.original_price:
            return f"PKR {self.original_price:,.0f}"
        return None

    @property
    def discount_percentage(self):
        """Calculate discount percentage if original price exists."""
        if self.original_price and self.original_price > self.price_per_day:
            return round(((self.original_price - self.price_per_day) / self.original_price) * 100)
        return 0


class Package(models.Model):
    """
    Model to store travel package information.
    Managed by Super Admin.
    """
    PACKAGE_TYPES = [
        ('city', 'City Break'),
        ('beach', 'Beach'),
        ('adventure', 'Adventure'),
        ('luxury', 'Luxury'),
        ('romantic', 'Romantic'),
        ('family', 'Family'),
        ('cultural', 'Cultural'),
        ('wellness', 'Wellness'),
    ]
    
    HIGHLIGHTS_CHOICES = [
        ('free_cancellation', 'Free Cancellation'),
        ('breakfast_included', 'Breakfast Included'),
        ('city_center', 'City Center'),
        ('beachfront', 'Beachfront'),
        ('all_inclusive', 'All-Inclusive'),
        ('spa_access', 'Spa Access'),
        ('central_location', 'Central Location'),
        ('free_wifi', 'Free WiFi'),
        ('gym_access', 'Gym Access'),
        ('traditional_experience', 'Traditional Experience'),
        ('near_shrines', 'Near Shrines'),
        ('historic_area', 'Historic Area'),
        ('afternoon_tea', 'Afternoon Tea'),
        ('museum_access', 'Museum Access'),
        ('private_beach', 'Private Beach'),
        ('butler_service', 'Butler Service'),
        ('mountain_views', 'Mountain Views'),
        ('ski_access', 'Ski Access'),
        ('theme_park_access', 'Theme Park Access'),
        ('kids_club', 'Kids Club'),
        ('family_rooms', 'Family Rooms'),
        ('overwater_villa', 'Overwater Villa'),
        ('snorkeling', 'Snorkeling'),
    ]
    
    title = models.CharField(max_length=200, help_text='Package title/name')
    destination = models.CharField(max_length=200, help_text='Destination city and country')
    description = models.TextField(blank=True, help_text='Detailed package description')
    
    # Hotel information
    hotel_name = models.CharField(max_length=200, help_text='Hotel name')
    hotel_location = models.CharField(max_length=200, help_text='Hotel location/address')
    hotel_stars = models.IntegerField(choices=[(i, f'{i} Star') for i in range(1, 6)], default=3)
    hotel_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    hotel_review_count = models.IntegerField(default=0)
    hotel_image_url = models.URLField(max_length=500, blank=True, help_text='Hotel image URL')
    
    # Flight information
    airline = models.CharField(max_length=100, help_text='Airline name')
    departure_airport = models.CharField(max_length=10, help_text='Departure airport code')
    arrival_airport = models.CharField(max_length=10, help_text='Arrival airport code')
    flight_duration = models.CharField(max_length=20, help_text='Flight duration (e.g., 7h 15m)')
    flight_stops = models.IntegerField(default=0, help_text='Number of stops')
    departure_time = models.CharField(max_length=10, help_text='Departure time (e.g., 08:30)')
    arrival_time = models.CharField(max_length=10, help_text='Arrival time (e.g., 21:45)')
    
    # Pricing
    price_per_person = models.DecimalField(max_digits=10, decimal_places=2, help_text='Price per person in PKR')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Original price for discount display')
    price_per_package = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Total package price in PKR')
    
    # Package details
    nights = models.IntegerField(default=1, help_text='Number of nights')
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES, help_text='Package category')
    highlights = models.JSONField(default=list, blank=True, help_text='List of highlight tags as strings')
    includes = models.JSONField(default=list, blank=True, help_text='List of included items as strings')
    
    # Availability and status
    availability = models.IntegerField(default=0, help_text='Number of available slots')
    bookings = models.IntegerField(default=0, help_text='Number of bookings made')
    is_featured = models.BooleanField(default=False, help_text='Is this a featured package?')
    is_popular = models.BooleanField(default=False, help_text='Is this a popular package?')
    is_active = models.BooleanField(default=True, help_text='Is the package currently active?')
    status = models.CharField(max_length=20, default='active', choices=[
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Package'
        verbose_name_plural = 'Packages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destination', 'is_active']),
            models.Index(fields=['package_type', 'is_active']),
            models.Index(fields=['price_per_person']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.destination}"

    @property
    def display_price(self):
        """Returns formatted price display."""
        return f"PKR {self.price_per_person:,.0f}"

    @property
    def display_original_price(self):
        """Returns formatted original price display."""
        if self.original_price:
            return f"PKR {self.original_price:,.0f}"
        return None

    @property
    def discount_percentage(self):
        """Calculate discount percentage if original price exists."""
        if self.original_price and self.original_price > self.price_per_person:
            return round(((self.original_price - self.price_per_person) / self.original_price) * 100)
        return 0

    @property
    def remaining_availability(self):
        """Calculate remaining available slots."""
        return max(0, self.availability - self.bookings)