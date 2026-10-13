"""Diff-only history record serializer.

Each row returns `{history_id, history_date, history_type, history_user, changed_fields}`.
For `+` (creation) records, `changed_fields` is omitted since there's no prior state.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class _HistoryUserSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    email = serializers.CharField(read_only=True)


class ProjectHistoryOutputSerializer(serializers.Serializer):
    history_id = serializers.UUIDField(read_only=True)
    history_date = serializers.DateTimeField(read_only=True)
    history_type = serializers.CharField(read_only=True)
    history_user = _HistoryUserSerializer(read_only=True, allow_null=True)
    changed_fields = serializers.SerializerMethodField()

    _TRACKED_FIELDS = ("name", "description", "status")

    def get_changed_fields(self, obj: Any) -> dict[str, dict[str, Any]] | None:
        prev = obj.prev_record
        if prev is None:
            return None
        delta = obj.diff_against(prev, included_fields=self._TRACKED_FIELDS)
        return {change.field: {"from": change.old, "to": change.new} for change in delta.changes}
