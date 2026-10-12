"""
Standard success envelope renderer.

Wraps non-paginated, non-error payloads in `{"data": ...}`. Paginated
responses already use `StandardPagination` which emits the envelope; error
responses are produced by `custom_exception_handler`. Both carry a top-level
`data` or `error` key, so this renderer leaves them untouched.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: Mapping[str, Any] | None = None,
    ) -> bytes:
        if data is None or self._already_wrapped(data):
            return super().render(data, accepted_media_type, renderer_context)
        return super().render({"data": data}, accepted_media_type, renderer_context)

    @staticmethod
    def _already_wrapped(data: Any) -> bool:
        return isinstance(data, dict) and bool({"data", "error"} & data.keys())
