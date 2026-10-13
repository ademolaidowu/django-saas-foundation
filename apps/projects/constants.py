from core.models.base import BaseTextChoices


class ProjectStatus(BaseTextChoices):
    PLANNING = "planning", "Planning"
    ACTIVE = "active", "Active"
    ON_HOLD = "on_hold", "On hold"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class TaskStatus(BaseTextChoices):
    TODO = "todo", "To do"
    IN_PROGRESS = "in_progress", "In progress"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


TERMINAL_TASK_STATUSES: frozenset[str] = frozenset({TaskStatus.DONE, TaskStatus.CANCELLED})
