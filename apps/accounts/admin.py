from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models.account import Account
from accounts.models.user import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active", "is_email_verified")
    list_filter = ("is_staff", "is_active", "is_email_verified")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified", "groups", "user_permissions")},
        ),
        ("Timestamps", {"fields": ("public_id", "last_login", "created_at", "modified_at", "deleted_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "first_name", "last_name"),
            },
        ),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "status", "is_primary", "joined_at")
    list_filter = ("status", "is_primary", "organization")
    search_fields = ("user__email", "organization__name", "organization__slug")
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at", "joined_at")
    raw_id_fields = ("user", "organization", "created_by", "modified_by", "deleted_by")
