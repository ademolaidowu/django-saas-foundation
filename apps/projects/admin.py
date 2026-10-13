from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from projects.models.project import Project
from projects.models.task import Task


@admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin):
    list_display = ("name", "organization", "status", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("name",)
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at")
    raw_id_fields = ("organization", "created_by", "modified_by", "deleted_by")


@admin.register(Task)
class TaskAdmin(SimpleHistoryAdmin):
    list_display = ("title", "project", "status", "assignee", "due_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)
    readonly_fields = ("public_id", "created_at", "modified_at", "deleted_at")
    raw_id_fields = (
        "organization",
        "project",
        "assignee",
        "created_by",
        "modified_by",
        "deleted_by",
    )
