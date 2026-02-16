from django.db import models


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
