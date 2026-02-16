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
]
