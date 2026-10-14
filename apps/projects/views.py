"""Projects + Tasks endpoints — thin views on top of selectors / services."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from access.decorators import require_permission
from core.exceptions import APIServiceError
from core.pagination import StandardPagination
from projects.exceptions import ProjectError, TaskError
from projects.selectors import ProjectSelectors, TaskSelectors
from projects.serializers.input.project import (
    ProjectCreateInputSerializer,
    ProjectUpdateInputSerializer,
)
from projects.serializers.input.task import (
    TaskCreateInputSerializer,
    TaskUpdateInputSerializer,
)
from projects.serializers.output.history import ProjectHistoryOutputSerializer
from projects.serializers.output.project import ProjectOutputSerializer
from projects.serializers.output.task import TaskOutputSerializer
from projects.services import ProjectService, TaskService


def _as_uuid(raw: str | None) -> uuid.UUID | None:
    if raw is None:
        return None
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError):
        return None


class ProjectsListView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("projects:read")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        organization = request.organization  # type: ignore[attr-defined]
        projects = ProjectSelectors.list_for_organization(
            organization,
            status=request.query_params.get("status") or None,
        )
        paginator = StandardPagination()
        page: Any = paginator.paginate_queryset(projects, request)
        return paginator.get_paginated_response(ProjectOutputSerializer(page, many=True).data)

    @require_permission("projects:create")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ProjectCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = ProjectService.create_project(
            organization=request.organization,  # type: ignore[attr-defined]
            name=serializer.validated_data["name"],
            description=serializer.validated_data["description"],
            status=serializer.validated_data["status"],
            actor=request.user,  # type: ignore[arg-type]
        )
        return Response(
            ProjectOutputSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request: Request, public_id):
        organization = request.organization  # type: ignore[attr-defined]
        project = ProjectSelectors.get_by_public_id(organization, public_id)
        if project is None:
            raise APIServiceError(
                error_code=ProjectError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return project

    @require_permission("projects:read")
    def get(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        project = self._get(request, public_id)
        return Response(ProjectOutputSerializer(project).data)

    @require_permission("projects:update")
    def patch(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        project = self._get(request, public_id)
        serializer = ProjectUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        project = ProjectService.update_project(
            project=project,
            actor=request.user,  # type: ignore[arg-type]
            name=serializer.validated_data.get("name"),
            description=serializer.validated_data.get("description"),
            status=serializer.validated_data.get("status"),
        )
        return Response(ProjectOutputSerializer(project).data)

    @require_permission("projects:delete")
    def delete(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        project = self._get(request, public_id)
        ProjectService.delete_project(project=project, actor=request.user)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("projects:read")
    def get(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        organization = request.organization  # type: ignore[attr-defined]
        project = ProjectSelectors.get_by_public_id(organization, public_id)
        if project is None:
            raise APIServiceError(
                error_code=ProjectError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        history_qs = project.history.all().select_related("history_user").order_by("-history_date")
        paginator = StandardPagination()
        page: Any = paginator.paginate_queryset(history_qs, request)
        return paginator.get_paginated_response(ProjectHistoryOutputSerializer(page, many=True).data)


class TasksListView(APIView):
    permission_classes = [IsAuthenticated]

    @require_permission("tasks:read")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        organization = request.organization  # type: ignore[attr-defined]
        tasks = TaskSelectors.list_for_organization(
            organization,
            status=request.query_params.get("status") or None,
            project_id=_as_uuid(request.query_params.get("project")),
            assignee_id=_as_uuid(request.query_params.get("assignee")),
        )
        paginator = StandardPagination()
        page: Any = paginator.paginate_queryset(tasks, request)
        return paginator.get_paginated_response(TaskOutputSerializer(page, many=True).data)

    @require_permission("tasks:create")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = TaskCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.create_task(
            organization=request.organization,  # type: ignore[attr-defined]
            actor=request.user,  # type: ignore[arg-type]
            project_id=serializer.validated_data["project_id"],
            title=serializer.validated_data["title"],
            description=serializer.validated_data["description"],
            status=serializer.validated_data["status"],
            assignee_id=serializer.validated_data["assignee_id"],
            due_date=serializer.validated_data["due_date"],
        )
        return Response(
            TaskOutputSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request: Request, public_id):
        organization = request.organization  # type: ignore[attr-defined]
        task = TaskSelectors.get_by_public_id(organization, public_id)
        if task is None:
            raise APIServiceError(
                error_code=TaskError.NotFound,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return task

    @require_permission("tasks:read")
    def get(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        task = self._get(request, public_id)
        return Response(TaskOutputSerializer(task).data)

    @require_permission("tasks:update")
    def patch(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        task = self._get(request, public_id)
        serializer = TaskUpdateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_task(
            task=task,
            actor=request.user,  # type: ignore[arg-type]
            data=serializer.validated_data,
        )
        return Response(TaskOutputSerializer(task).data)

    @require_permission("tasks:delete")
    def delete(self, request: Request, public_id, *args: Any, **kwargs: Any) -> Response:
        task = self._get(request, public_id)
        TaskService.delete_task(task=task, actor=request.user)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)
