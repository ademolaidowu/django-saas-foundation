from django.contrib import admin

from tenants.models.organization import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at")
