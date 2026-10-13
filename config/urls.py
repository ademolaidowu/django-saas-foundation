from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"data": {"status": "ok"}})


urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/auth/", include("accounts.urls", namespace="accounts")),
    path("api/access/", include("access.urls", namespace="access")),
    path("api/", include("projects.urls", namespace="projects")),
    path("admin/", admin.site.urls),
]
