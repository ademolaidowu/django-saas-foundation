# Architecture

The one-line claim this project makes: **no HTTP response leaves this server with another organization's row in it.** Everything below explains how.

## The chain, in order

A `GET /api/projects/` from an authenticated client walks this path:

1. **gunicorn** receives the HTTP request, hands the socket to a worker.
2. **DRF `Request`** wraps the WSGI env.
3. **`AccountTokenAuthentication`** (`apps/accounts/authentication.py`) reads the auth cookie (header fallback for mobile/local). It executes **one** SQL query: `SELECT ... FROM knox_authtoken JOIN account_tokens JOIN accounts JOIN organizations WHERE token_key = ?`. If anything along that chain is missing — token revoked, `AccountToken` row deleted, `Account.status != ACTIVE` — the request fails 401 before reaching the view.
4. On success, the auth class **attaches `request.user`, `request.account`, `request.organization`** to the DRF request. The client never names the organization; it is derived from the token.
5. **View dispatch.** The view's `permission_classes = [IsAuthenticated]` has already passed by now. The method handler fires.
6. **`@require_permission("projects:read")`** (`apps/access/decorators.py`) runs one `EXISTS` query against `role_assignments → role → role_permissions → permission` for the current `request.account`. Miss → `APIServiceError(PermissionDenied, status_code=403)`. Hit → the handler proceeds.
7. **Selector call.** `ProjectSelectors.list_for_organization(request.organization, status=…)` — the view hands `request.organization` down the chain explicitly. The selector never looks at thread-locals, never reaches into the request.
8. **`TenantScopedQuerySet.for_organization(org)`** (`apps/core/models/tenancy.py`) applies `.filter(organization=org)` and flips `_tenant_scoped = True`. If any ancestor of this queryset tried to evaluate without this call, every evaluation hook (`_fetch_all`, `count`, `exists`, `get`, `first`, `last`, `update`, `delete`) would raise `UnscopedQueryError` immediately.
9. **Postgres** returns rows filtered by `organization_id`. Nothing else is visible.
10. **Serializer** shapes the response, **envelope renderer** wraps it in `{"data": [...], "meta": {...}}`, and the response leaves the worker.

## The three layers of enforcement

Tenant isolation is not one mechanism; it's three independent ones that each fail-closed. Removing any one still leaves the other two:

1. **Token binding** (service-level, at mint time). `return_response_with_auth_cookie` in `apps/accounts/cookies.py` creates the Knox `AuthToken` and the `AccountToken` row in one atomic transaction. A token is born with its `account_id` immutable. There is no API to change an `AccountToken.account_id` on an existing row.
2. **Authentication** (per request, fail-closed). `AccountTokenAuthentication` requires the full chain `AuthToken → AccountToken → Account → Organization` to resolve. If any link is deleted — e.g. an attacker drops the `AccountToken` row — the next request from that cookie is 401.
3. **Queryset guard** (per query, fail-closed). `TenantScopedQuerySet` refuses to evaluate without `.for_organization(org)`. Developers can't forget to filter; the ORM won't let them.

Each layer is tested independently (`tests/accounts/test_token_isolation.py`, `tests/accounts/test_me.py`, `tests/core/test_tenant_isolation.py`) and in combination (`tests/isolation/test_endpoint_isolation.py` — the parametrised matrix across every tenant-scoped endpoint).

## Where RBAC fits

Tenancy is attached **before** permissions are checked. By the time `@require_permission("projects:read")` runs, `request.organization` is already set from the token — RBAC never has to decide "which org are we checking in?". That ordering is why the two deny paths never overlap:

- **Cross-tenant** → the selector returns `None`/empty via `.for_organization(…)`, the view responds **404**. The resource isn't in the user's world.
- **Same-tenant, wrong permission** → `@require_permission` raises `APIServiceError(PermissionDenied, 403)`. The resource is in the user's world; they just can't do this action.

ADR 005 writes this contract down.

## What happens on a write

The same chain, with four additions:

- **`request.user` populates `created_by` / `modified_by` / `deleted_by`.** Services take `*, actor: User` and set these fields. The `AuditTrailMixin.delete(deleted_by=...)` wrapper rejects soft-deletes without an actor.
- **`simple-history` middleware** (`simple_history.middleware.HistoryRequestMiddleware`) captures `request.user` into a thread-local. On every save/delete of a `HistoricalRecords`-wrapped model (`Project`, `Task`, `Role`, `RoleAssignment`), simple-history writes a parallel history row with `history_user` populated from that thread-local. ADR 006 explains why `request.user` and not `request.account` — user-level attribution is what the audit log needs.
- **`@transaction.atomic`** wraps every service method. If anything downstream raises — the policy check, a serializer validation, a DB integrity error — the whole chain rolls back. No orphan rows, no half-created users on a failed registration.
- **Policies run inside the service**, not in the view. `TaskPolicy.can_close(task, account)` in `apps/projects/policies.py` is called from `TaskService.update_task` when the request would transition `status` to a terminal value. Policy denial is a 403 raised from the service.

## The one escape hatch

`TenantScopedQuerySet.unsafe_all()` exists. It flips the `_tenant_scoped` flag without filtering, logs a `RuntimeWarning`, and lets the query run. It is used in exactly two code sites:

- `apps/projects/management/commands/seed_demo.py` — the summary `.count()` at the end of the command.
- The Django admin (deferred — admin reads via `_default_manager._base_manager` which bypasses the guard entirely for migrations/`loaddata`/`dumpdata`).

Any grep against `.unsafe_all()` is a code-review checkpoint. A new call site should be justified in the PR description, and the warning in the server log makes any accidental use visible in production.

## References

- `docs/decisions/` — the six ADRs that freeze every design decision referenced above.
- `tests/isolation/test_endpoint_isolation.py` — the parametrised matrix that proves the one-line claim.
- `tests/accounts/test_token_isolation.py` — the token-rotation + stale-cookie proof.
- `tests/access/test_permission_matrix.py` — the role × endpoint grid that keeps the RBAC story honest.
