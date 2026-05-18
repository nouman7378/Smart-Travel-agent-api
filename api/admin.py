from django.contrib import admin
from django.utils.html import format_html
from .models import Hotel, Room, City, Car, Package


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'stars', 'rating', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px; max-width: 120px; border-radius: 4px; object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_type', 'hotel', 'price_per_night', 'available_rooms', 'room_image_preview')
    readonly_fields = ('room_image_preview',)

    def room_image_preview(self, obj):
        if obj.room_image:
            return format_html('<img src="{}" style="max-height: 80px; max-width: 120px; border-radius: 4px; object-fit: cover;" />', obj.room_image.url)
        return "No Image"
    room_image_preview.short_description = 'Preview'


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('model', 'company', 'price_per_day', 'is_available', 'car_image_preview')
    readonly_fields = ('car_image_preview',)

    def car_image_preview(self, obj):
        if obj.car_image:
            return format_html('<img src="{}" style="max-height: 80px; max-width: 120px; border-radius: 4px; object-fit: cover;" />', obj.car_image.url)
        return "No Image"
    car_image_preview.short_description = 'Preview'


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination', 'price_per_person', 'status', 'hotel_image_preview')
    readonly_fields = ('hotel_image_preview',)

    def hotel_image_preview(self, obj):
        if obj.hotel_image:
            return format_html('<img src="{}" style="max-height: 80px; max-width: 120px; border-radius: 4px; object-fit: cover;" />', obj.hotel_image.url)
        return "No Image"
    hotel_image_preview.short_description = 'Preview'


admin.site.register(City)
