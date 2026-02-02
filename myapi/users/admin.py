from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ActivationToken, UUIDUser


# Register custom User with full Django Admin interface
@admin.register(UUIDUser)
class MyUserAdmin(UserAdmin):
    # Fields that will appear in the user list
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')

    # Fields for search
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # Filters in the sidebar
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')

    # Organization of fields in the edit form
    fieldsets = UserAdmin.fieldsets + (
        ('UUID Info', {'fields': ('id',)}),  # Shows UUID (read-only)
    )

    # Read-only fields
    readonly_fields = ('id', 'date_joined', 'last_login')


@admin.register(ActivationToken)
class ActivationTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_expired', 'is_used', 'created_at', 'expires_at')
    list_filter = ('created_at', 'expires_at', 'used_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'user', 'created_at', 'updated_at')
    ordering = ('-created_at',)
