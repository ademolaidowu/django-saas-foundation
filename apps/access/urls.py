from django.urls import path

from access.views import (
    PermissionsListView,
    RoleAssignmentCreateView,
    RoleAssignmentRevokeView,
    RoleDetailView,
    RolesListView,
)

app_name = "access"

urlpatterns = [
    path("permissions/", PermissionsListView.as_view(), name="permissions"),
    path("roles/", RolesListView.as_view(), name="roles"),
    path("roles/<uuid:public_id>/", RoleDetailView.as_view(), name="role-detail"),
    path(
        "role-assignments/",
        RoleAssignmentCreateView.as_view(),
        name="role-assignments",
    ),
    path(
        "role-assignments/<uuid:public_id>/",
        RoleAssignmentRevokeView.as_view(),
        name="role-assignment-revoke",
    ),
]
