from django.urls import path

from projects.views import (
    ProjectDetailView,
    ProjectHistoryView,
    ProjectsListView,
    TaskDetailView,
    TasksListView,
)

app_name = "projects"

urlpatterns = [
    path("projects/", ProjectsListView.as_view(), name="projects"),
    path("projects/<uuid:public_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<uuid:public_id>/history/",
        ProjectHistoryView.as_view(),
        name="project-history",
    ),
    path("tasks/", TasksListView.as_view(), name="tasks"),
    path("tasks/<uuid:public_id>/", TaskDetailView.as_view(), name="task-detail"),
]
