# ADR 006 — Middleware-driven history user attribution

**Status:** Accepted
**Phase:** 4 (Example domain + audit)

## Context

`django-simple-history` tracks changes by writing a parallel row to a `*_history` table on every save/delete. The question is: *who* did the change? For the audit log to answer "who edited this project yesterday," each historical row needs a `history_user` FK pointing at an actual user — not just a timestamp.

Two shapes exist for populating it:

1. **Middleware-driven (library default).** `simple_history.middleware.HistoryRequestMiddleware` captures `request.user` on every HTTP request and stashes it in a thread-local. The simple-history model-save signal reads that thread-local and sets `history_user`. Zero code to maintain; works out of the box for every request.
2. **Signal-driven override.** Register a custom `history_user_setter` with simple-history that fetches whatever we want (e.g. `request.account` instead of `request.user`). Gives us account-level attribution — matches our Phase 2 "token binds to Account, not User" discipline — but costs a per-model callback and a chunk of custom code.

## Decision

Use the library's `HistoryRequestMiddleware`. User-level attribution — "Alice edited this project" — is enough for the audit story this starter is making. Account-level attribution ("Alice's Acme account did this") would be more precise, but it duplicates information already visible from the `AuditTrailMixin` (`created_by` / `modified_by` / `deleted_by`) and from the row's own org FK.

Rationale:

- The historical row's org context is already fully determined by the current-model row it attaches to (every tenant-scoped model has `organization_id` on both the live row and every history row).
- `request.user` is unambiguous — one person, one email. `request.account` would require resolving the user from the account for display anyway, so the net readability win is small.
- Zero custom code; one line of settings. Phase 3's exceptions prove that complexity has a tax.

## Consequences

- `history_user` is a FK to `AUTH_USER_MODEL = accounts.User`. For API or shell edits with no logged-in user (background jobs, management commands run as root), `history_user` is `None`. The `ProjectHistoryOutputSerializer` handles the null gracefully (`"history_user": null`).
- The history endpoint response is lean — just `email` and `public_id` under `history_user`. If we ever need org-identity in the audit view, we can join via the historical row's own `organization_id`.
- The thread-local is cleared at the end of each request by the middleware, so there's no cross-request leakage.
- Management-command edits (e.g. `seed_demo` writing a project) show up with `history_user=None`. Acceptable — those edits are system-generated and the row's `created_by` is still the demo "Alice" user who nominally owns them.

## Extension path (future)

If a later phase needs account-level attribution (e.g. "which org-identity was active?"), we can swap in `simple_history.register_history_user_setter(get_history_user)` where `get_history_user(instance)` reads `request.account` off the thread-local request. The migration cost is one function and one `AppConfig.ready()` registration. We don't do that now.

## References

- `config/settings/base.py` — `SIMPLE_HISTORY_REVERT_DISABLED = True` + middleware entry.
- `apps/projects/serializers/output/history.py` — diff-only output; nulls on `history_user` handled.
- `tests/projects/test_history.py` — asserts `history_user` is set on request-driven edits and `None` on shell/management edits.
