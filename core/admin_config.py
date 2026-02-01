"""
Custom admin site: dashboard and auth-related sections only (Users, Groups).
Superadmin has access only to this admin, not to other Django admin apps.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group

User = get_user_model()


class SuperAdminSite(admin.AdminSite):
    site_header = 'Smart-Travel-Planner Admin'
    site_title = 'Admin'
    index_title = 'Dashboard'


# Custom admin site with only Users and Groups (dashboard + auth sections)
superadmin_site = SuperAdminSite(name='superadmin')

superadmin_site.register(User, UserAdmin)
superadmin_site.register(Group, GroupAdmin)
