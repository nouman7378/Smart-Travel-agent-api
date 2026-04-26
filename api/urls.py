"""
URL configuration for api app.
"""
from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('login/', views.login_api, name='login'),
    path('signup/', views.signup_api, name='signup'),
    path('bookings/cart/', views.booking_cart_api, name='booking_cart'),
    path('bookings/cart/add/', views.booking_cart_add_api, name='booking_cart_add'),
    path('flights/search/', views.flight_search_api, name='flight_search'),
    path('cities/search/', views.city_search_api, name='city_search'),
    
    # Hotel APIs - Public
    path('hotels/', views.hotel_list_api, name='hotel_list'),
    path('hotels/<int:hotel_id>/', views.hotel_detail_api, name='hotel_detail'),
    
    # Hotel APIs - Admin Only
    path('admin/hotels/', views.hotel_admin_list_api, name='hotel_admin_list'),
    path('admin/hotels/create/', views.hotel_create_api, name='hotel_create'),
    path('admin/hotels/<int:hotel_id>/update/', views.hotel_update_api, name='hotel_update'),
    path('admin/hotels/<int:hotel_id>/delete/', views.hotel_delete_api, name='hotel_delete'),
    
    # Room APIs - Public
    path('hotels/<int:hotel_id>/rooms/', views.hotel_rooms_api, name='hotel_rooms'),
    
    # Room APIs - Admin Only
    path('admin/hotels/<int:hotel_id>/rooms/', views.room_admin_list_api, name='room_admin_list'),
    path('admin/hotels/<int:hotel_id>/rooms/create/', views.room_create_api, name='room_create'),
    path('admin/rooms/<int:room_id>/update/', views.room_update_api, name='room_update'),
    path('admin/rooms/<int:room_id>/delete/', views.room_delete_api, name='room_delete'),
    
    # Car APIs - Public
    path('cars/', views.car_list_api, name='car_list'),
    path('cars/<int:car_id>/', views.car_detail_api, name='car_detail'),
    
    # Car APIs - Admin Only
    path('admin/cars/', views.car_admin_list_api, name='car_admin_list'),
    path('admin/cars/create/', views.car_create_api, name='car_create'),
    path('admin/cars/<int:car_id>/update/', views.car_update_api, name='car_update'),
    path('admin/cars/<int:car_id>/delete/', views.car_delete_api, name='car_delete'),
    
    # Package APIs - Public
    path('packages/', views.package_list_api, name='package_list'),
    path('packages/<int:package_id>/', views.package_detail_api, name='package_detail'),
    
    # Package APIs - Admin Only
    path('admin/packages/', views.package_admin_list_api, name='package_admin_list'),
    path('admin/packages/create/', views.package_create_api, name='package_create'),
    path('admin/packages/<int:package_id>/update/', views.package_update_api, name='package_update'),
    path('admin/packages/<int:package_id>/delete/', views.package_delete_api, name='package_delete'),
    
    # User Management APIs - Admin Only
    path('admin/users/', views.admin_user_list_api, name='admin_user_list'),

    # AI Assistant APIs
    path('ai/chat/', views.ai_chat_api, name='ai_chat'),
    path('ai/itinerary/', views.ai_itinerary_api, name='ai_itinerary'),
    path('ai/itineraries/<int:itinerary_id>/', views.ai_itinerary_detail_api, name='ai_itinerary_detail'),
]
