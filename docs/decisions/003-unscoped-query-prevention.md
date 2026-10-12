# ADR 003 — Preventing unscoped queries on tenant-scoped models

**Status:** Accepted
**Phase:** 1 (Core and tenancy)

## Context

Row-level multitenancy (ADR 001) means every tenant-owned row carries an `organization_id` and queries must filter on it. The hazard is boring but severe: a developer writes `Project.objects.filter(status="open")` instead of `Project.objects.filter(status="open", organization=request.organization)`, and the API silently returns another tenant's data. Code review catches this most of the time. "Most of the time" is not a tenancy story.

Two levels of defense exist in the wild:
1. **Explicit filtering in selectors + policies.** Treat the discipline as a code review concern. Both reference projects (`sonecare-api`, `sparkle-commerce-api`) take this path.
2. **A guard at the ORM layer.** Make the queryset refuse to evaluate until a scoping method has been called. Developers get a loud failure in test; prod code physically can't skip the step.

(1) is simpler but leaky. (2) is the point of this repo.

## Decision

Introduce a `TenantScopedQuerySet` (and `TenantManager` / `TenantRecordsManager`) that:

- Carries a private `_tenant_scoped` boolean, default `False`, preserved across `_clone` and `_chain` so every chained operation inherits scope state.
- Exposes `.for_organization(org)` as the sanctioned scoping entry point. It filters by the FK and sets `_tenant_scoped=True`. Passing `None` raises immediately.
- Exposes `.unsafe_all()` as the explicit, documented opt-out. It marks the queryset scoped and emits a `RuntimeWarning` so bypasses show up in logs.
- Overrides every evaluation path — `_fetch_all`, `iterator`, `count`, `exists`, `get`, `first`, `last`, `update`, `delete` — to call `_check_scoped()` first. If the queryset isn't scoped and `TENANT_GUARD_ENABLED` is true, `_check_scoped()` raises `UnscopedQueryError` in `strict` mode or warns in `warn` mode.
- Reverse accessors (`organization.project_set.all()`) auto-scope: Django's `RelatedManager` sets `self.instance` before calling `get_queryset()`, and `TenantManager.get_queryset()` uses that signal to pre-mark the queryset.

Mode is a settings flag:

```
TENANT_GUARD_ENABLED = True        # off switch of last resort
TENANT_GUARD_MODE = "strict"       # "strict" raises, "warn" warns
```

`test.py` pins `TENANT_GUARD_MODE="strict"` regardless of env — the tests are where the discipline is proven.

## Consequences

**What works unchanged:**

- `Organization.objects.all()` — `Organization` extends `BaseModel`, not `TenantScopedModel`. It *is* the tenant.
- `migrations`, `loaddata`, `dumpdata` — Django uses `_base_manager`, which skips our managers; these commands operate on the raw queryset.
- Reverse FK accessors — pre-marked scoped by the `RelatedManager.instance` signal.
- Chained operations — `.filter(...)`, `.exclude(...)`, `.order_by(...)` propagate the scope flag through `_clone` / `_chain`.

**What needs adaptation:**

- **Django admin.** Admin changelist calls `self.get_queryset(request).all()`. Register tenant models through a `TenantAdmin` base (deferred to Phase 2 when the first user model lands) that calls `.unsafe_all()` and injects an organization filter in the UI.
- **Shell / scripts.** Use `.unsafe_all()` or temporarily set `TENANT_GUARD_MODE="warn"` via `django.test.utils.override_settings` in management commands.
- **Learning curve.** New contributors see `UnscopedQueryError` on their first fresh test. Error message points at `.for_organization(...)`.

**What this costs:**

- Every evaluation path on `TenantScopedQuerySet` has a two-line `_check_scoped()` prelude. Measured overhead: negligible — a dict-attr lookup. 
- Debugging raw SQL from the shell requires `.unsafe_all()` or settings override.
- The `related_name="+"` default on `TenantScopedModel.organization` suppresses reverse accessors; child models must override `related_name` (and `related_query_name`) if they want `organization.project_set`.

## Alternatives considered

- **DEBUG-only guard.** Rejected: the whole point is to make prod incidents impossible. A guard that only fires in test leaves prod unprotected.
- **Signal / middleware that attaches `request.organization` to every query.** Rejected: too much magic, breaks background jobs and management commands.
- **Row-level security in Postgres.** Future consideration — complementary, not a replacement. Postgres RLS enforces at the DB, but requires `SET LOCAL app.current_org = …` on every connection and conflicts with Django's connection pooling patterns. Revisit if there's a compelling need (ADR candidate for Phase 2+).

## References

- `apps/core/models/tenancy.py` — implementation
- `apps/core/exceptions.py` — `UnscopedQueryError`
- `tests/core/test_tenant_isolation.py` — proves the guard fires on every evaluation path
- `config/settings/tenancy.py` — the toggles
