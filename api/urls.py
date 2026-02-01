"""
URL configuration for api app.
"""
from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('login/', views.login_api, name='login'),
    path('signup/', views.signup_api, name='signup'),
]
