"""
URL configuration for api app.
"""
from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('login/', views.login_api, name='login'),
    path('signup/', views.signup_api, name='signup'),
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
]
