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