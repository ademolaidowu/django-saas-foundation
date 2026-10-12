"""
Test-only URLconf — overridden via `@pytest.mark.urls(...)` in the token
isolation test. Exposes two endpoints:

    GET  /probe/me          → organization slug derived from request.organization
    GET  /probe/widgets     → count of widgets the current token can see

The slug comes straight from the authentication class's attached context, so
the test proves that `request.organization` is derived from the token chain
and not from any client-supplied value.
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Captured at test setup — see test_token_isolation.py's fixture.
_WIDGET_MODEL = None


def set_widget_model(model) -> None:
    global _WIDGET_MODEL
    _WIDGET_MODEL = model


class ProbeMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({"organization_slug": request.organization.slug})


class ProbeWidgetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        count = _WIDGET_MODEL.records.for_organization(request.organization).count()
        return Response({"count": count})


urlpatterns = [
    path("api/auth/", include("accounts.urls", namespace="accounts")),
    path("probe/me/", ProbeMeView.as_view()),
    path("probe/widgets/", ProbeWidgetsView.as_view()),
]
