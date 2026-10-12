"""
Pagination — the standard envelope.

Mirrors the project's `{"data": ..., "meta": ...}` success format. Views that
return a `PageNumberPagination`-paginated response already produce this shape;
non-paginated responses get wrapped by `EnvelopeJSONRenderer`.
"""

from __future__ import annotations

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data: Any) -> Response:
        assert self.page is not None and self.request is not None
        return Response(
            {
                "data": data,
                "meta": {
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total": self.page.paginator.count,
                    "pages": self.page.paginator.num_pages,
                },
            }
        )
