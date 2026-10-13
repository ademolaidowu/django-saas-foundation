from __future__ import annotations

from django.contrib import admin

from access.models.assignment import RoleAssignment
from access.models.permission import Permission
from access.models.role import Role, RolePermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "module", "description")
    list_filter = ("module",)
    search_fields = ("code", "module")
    readonly_fields = ("public_id", "code", "module", "description", "created_at", "modified_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    raw_id_fields = ("permission",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "is_system", "created_at")
    list_filter = ("is_system", "organization")
    search_fields = ("name", "code", "organization__name")
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at")
    raw_id_fields = ("organization", "created_by", "modified_by", "deleted_by")
    inlines = [RolePermissionInline]


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("account", "role", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("account__user__email", "role__name")
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at")
    raw_id_fields = ("account", "role", "created_by", "modified_by", "deleted_by")
