# ADR 005 — 404, not 403, for cross-tenant access

**Status:** Accepted
**Phase:** 3 (Access control)

## Context

Two distinct deny paths show up on every authenticated endpoint:

1. **The resource belongs to a different organization.** A user authenticated for Org Alpha asks for a Bravo-owned Project. The row exists, but not in a world the token can see.
2. **The user is in the right organization but lacks the permission.** A Viewer-role user calls `POST /api/access/roles/` on their own org. The row they're trying to create *would* be theirs — they just can't do that action.

HTTP has two status codes for "no, you can't have this": **403 Forbidden** ("I know what you want and refuse") and **404 Not Found** ("there is no such thing"). Picking the wrong one leaks data: a 403 on a cross-tenant resource confirms the resource exists.

## Decision

- **Cross-tenant access → 404.** The resource exists in the database but not in the organization the token acts on; from the client's perspective, it does not exist. Returning 403 would confirm that *something* is at that URL — enough for an attacker to enumerate IDs. Phase 1's `TenantScopedQuerySet` enforces this at the ORM layer: queries without `.for_organization(…)` raise, scoped queries silently exclude other orgs' rows, lookups by `public_id` outside the scope return `None`, and the view returns 404.
- **Same-tenant RBAC denial → 403.** The permission check (`@require_permission(...)` or inline) is the one place that returns 403. The resource either exists or doesn't within the user's own organization; the status code just says "you can't do this action."

The two code paths never overlap: tenancy is enforced first (via the auth class attaching `request.organization` and selectors scoping on it), then RBAC runs on the already-scoped set.

## Consequences

- **Enumeration-safe.** A client that doesn't belong to Org Bravo cannot discover whether a given `public_id` points to a Bravo-owned resource. They get 404 whether the ID exists in Bravo, exists in a third org, or doesn't exist at all.
- **Honest.** Within your own org, 403 means what it says: the resource is there, you're authenticated, you lack a permission. No obfuscation; the frontend can show "ask your admin for the `projects.create` permission" rather than a misleading "not found."
- **Simple mental model.** "Different org → 404. Same org, wrong permission → 403." No judgment calls at the view layer.
- **UUIDs make it workable.** Public IDs are UUIDv7 (per ADR 004), so an attacker can't guess them even if they knew the ID space existed. A sequential integer would make 404 a weak defense.

## Enforcement

- **Tenancy (404):** `TenantScopedQuerySet.for_organization(org)` in `apps/core/models/tenancy.py`; selectors in each app call it on every lookup. View returns 404 when `selector.get_by_public_id(...)` returns `None`.
- **RBAC (403):** `@require_permission("...")` in `apps/access/decorators.py`. Raises `APIServiceError(PermissionDenied, status_code=403)`.
- **Tests:** `tests/accounts/test_token_isolation.py` covers the 404 path across orgs. `tests/access/test_require_permission.py` covers the 403 path.

## References

- `docs/decisions/003-unscoped-query-prevention.md` — companion guarantee at the ORM layer.
- `docs/decisions/004-public-uuids-alongside-integer-pks.md` — why UUIDs make the 404 defense meaningful.
- `apps/access/decorators.py` — the 403 producer.
- `apps/core/models/tenancy.py` — the 404 producer (via empty scoped querysets).
