from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "is_staff", "is_active", "created_at")
    search_fields = ("email", "display_name")
    list_filter = ("is_staff", "is_active")
