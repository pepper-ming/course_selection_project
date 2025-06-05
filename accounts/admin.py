from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'name', 'role', 'email', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('額外資訊', {'fields': ('name', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('額外資訊', {'fields': ('name', 'role', 'email')}),
    )