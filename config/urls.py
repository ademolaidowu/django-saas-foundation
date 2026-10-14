from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    return JsonResponse({"data": {"status": "ok"}})


urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/auth/", include("accounts.urls", namespace="accounts")),
    path("api/access/", include("access.urls", namespace="access")),
    path("api/", include("projects.urls", namespace="projects")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("admin/", admin.site.urls),
]
