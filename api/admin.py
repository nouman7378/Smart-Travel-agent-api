from django.contrib import admin
from .models import Hotel, Room, City, Car, Package

# Register your models here.
admin.site.register(Hotel)
admin.site.register(Room)
admin.site.register(City)
admin.site.register(Car)
admin.site.register(Package)
