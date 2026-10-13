"""Access-control endpoints — thin views that gate via `@require_permission`."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from access.decorators import require_permission
from access.exceptions import RoleAssignmentError, RoleError
from access.models.account_lookup import _get_account_by_public_id_in_organization
from access.selectors import (
    PermissionSelectors,
    RoleAssignmentSelectors,
    RoleSelectors,
)
from access.serializers.input.assignment import RoleAssignmentCreateInputSerializer
from access.serializers.input.role import (
    RoleCreateInputSerializer,
    RoleUpdateInputSerializer,
)
from access.serializers.output.assignment import RoleAssignmentOutputSerializer
from access.serializers.output.permission import PermissionOutputSerializer
from access.serializers.output.role import RoleOutputSerializer
from access.services import RoleAssignmentService, RoleService
from core.exceptions import APIServiceError


class PermissionsListView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("permissions.read")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        permissions = PermissionSelectors.all()
        return Response(PermissionOutputSerializer(permissions, many=True).data)


class RolesListView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("roles.read")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        roles = RoleSelectors.list_for_organization(request.organization)  # type: ignore[attr-defined]
        return Response(RoleOutputSerializer(roles, many=True).data)

    @require_permission("roles.create")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = RoleCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = RoleService.create_role(
            organization=request.organization,  # type: ignore[attr-defined]
            name=serializer.validated_data["name"],
            description=serializer.validated_data["description"],
            permission_codes=serializer.validated_data["permission_codes"],
            created_by=request.user,  # type: ignore[arg-type]
        )
        return Response(
            RoleOutputSerializer(role).data,
            status=status.HTTP_201_CREATED,
        )


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request: Request, public_id):
        role = RoleSelectors.get_by_public_id(request.organization, public_id)  # type: ignore[attr-defined]
        if role is None:
            raise APIServiceError(
                error_code=RoleError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return role

    @require_permission("roles.read")
    def get(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        role = self._get(request, public_id)
        return Response(RoleOutputSerializer(role).data)

    @require_permission("roles.update")
    def patch(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        role = self._get(request, public_id)
        serializer = RoleUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        RoleService.update_role(
            role=role,
            updated_by=request.user,  # type: ignore[arg-type]
            name=serializer.validated_data.get("name"),
            description=serializer.validated_data.get("description"),
            permission_codes=serializer.validated_data.get("permission_codes"),
        )
        # Re-fetch with a fresh prefetch so the serializer reflects any
        # permission-code replacement the service just performed.
        role = RoleSelectors.get_by_public_id(request.organization, public_id)  # type: ignore[attr-defined]
        return Response(RoleOutputSerializer(role).data)

    @require_permission("roles.delete")
    def delete(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        role = self._get(request, public_id)
        RoleService.delete_role(role=role, deleted_by=request.user)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleAssignmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("role_assignments.create")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = RoleAssignmentCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = _get_account_by_public_id_in_organization(
            organization=request.organization,  # type: ignore[attr-defined]
            public_id=serializer.validated_data["account_id"],
        )
        if account is None:
            raise APIServiceError(
                error_code=RoleAssignmentError.AccountNotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        role = RoleSelectors.get_by_public_id(
            request.organization,  # type: ignore[attr-defined]
            serializer.validated_data["role_id"],
        )
        if role is None:
            raise APIServiceError(
                error_code=RoleError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        assignment = RoleAssignmentService.assign(
            account=account,
            role=role,
            assigned_by=request.user,  # type: ignore[arg-type]
        )
        return Response(
            RoleAssignmentOutputSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class RoleAssignmentRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("role_assignments.delete")
    def delete(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        assignment = RoleAssignmentSelectors.get_by_public_id(public_id)
        if (
            assignment is None or assignment.role.organization_id != request.organization.id  # type: ignore[attr-defined]
        ):
            raise APIServiceError(
                error_code=RoleAssignmentError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        RoleAssignmentService.revoke(assignment=assignment, revoked_by=request.user)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)
