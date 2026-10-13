from core.exceptions import BaseAPIErrorCode


class ProjectError:
    class NotFound(BaseAPIErrorCode):
        code = "project_0001"
        detail = "Project not found."


class TaskError:
    class NotFound(BaseAPIErrorCode):
        code = "task_0001"
        detail = "Task not found."

    class ProjectRequired(BaseAPIErrorCode):
        code = "task_0002"
        detail = "A task must belong to a project in this organization."

    class AssigneeNotInOrganization(BaseAPIErrorCode):
        code = "task_0003"
        detail = "The assignee must be a member of this organization."

    class NotAllowedToClose(BaseAPIErrorCode):
        code = "task_0004"
        detail = "Only the assignee or an admin can close this task."
