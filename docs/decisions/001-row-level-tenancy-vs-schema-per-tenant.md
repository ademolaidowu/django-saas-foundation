# ADR 001 — Row-level tenancy, not schema-per-tenant

**Status:** Accepted
**Phase:** 1 (Core and tenancy)

## Context

Multitenant Django apps have two canonical isolation shapes.

- **Row-level tenancy.** One schema, one set of tables. Every tenant-owned row carries an `organization_id`. Every query scopes on it. The library ecosystem is just Django — no plugin required.
- **Schema-per-tenant.** One Postgres schema per tenant, selected per request via `SET search_path`. The `django-tenants` package implements this on top of PostgreSQL's schema feature.

The two look superficially similar from the application code — "add tenant to a FK" vs. "flip a schema name" — but they have very different operational characteristics. The question for this starter is: **which default is cheaper to run and safer to reason about for the kind of web SaaS this repo targets?**

## Decision

**Row-level tenancy, with a strict ORM-layer guard** (see ADR 003) and **404-not-403** cross-tenant posture (see ADR 005). `django-tenants` is a thoughtful library, but it is the wrong default here. Four reasons:

1. **Migrations.** Row-level: `python manage.py migrate` touches one logical schema. Schema-per-tenant: every new tenant spawns a Postgres schema; every migration must run against each schema; onboarding scripts have to loop. In practice teams end up with a "did tenant N get the migration?" footgun and a migration runbook that scales with tenant count. For a project this size, the velocity cost outweighs the physical-isolation win.

2. **Connection pooling.** Row-level: one connection pool, flat. Any pgbouncer mode (session, transaction, statement) just works. Schema-per-tenant: Django's `django-tenants` middleware issues `SET search_path = tenant_X` on the connection. In pgbouncer **transaction pooling** — the default for high-concurrency setups — the `SET` is pinned to a transaction and lost on the next checkout. Teams either downgrade to session pooling (lower concurrency ceiling) or add tenant-aware connection routing. Both costs are real.

3. **Cross-tenant reporting.** Row-level: `SELECT COUNT(*) FROM projects` just works for the platform admin. Schema-per-tenant: either UNION ALL across every schema at query time (slow, fragile, breaks when a tenant is onboarding) or run a nightly ETL that denormalises every tenant's data back to a shared reporting schema. Either way, the "simple admin dashboard" becomes a pipeline.

4. **Operational cost.** Row-level: one database, one logical backup, one restore. Schema-per-tenant: `pg_dump` output grows roughly linearly with tenant count; a single-tenant restore requires schema-level selective restore; monitoring queries grow table-count-wise.

## Consequences

**What this buys:**
- Zero plugin dependency — just Django + PostgreSQL. The behavior is auditable with `grep organization_id`.
- Flat migrations, flat pool, flat backups. One mental model.
- Admin + reporting work by default.

**What this costs:**
- Isolation is **logical**, not physical. A SQL bug anywhere in the project (missing `WHERE organization_id = …`) is in principle a cross-tenant leak. This is the risk `django-tenants` eliminates at the schema level, and it's the risk this starter spends ADR 003 (strict `TenantScopedQuerySet` guard) and ADR 005 (404-not-403 posture) + the `tests/isolation/` matrix defending against. Those three mechanisms turn "please remember to filter" into "the ORM refuses to run without a filter, and the tests prove it."

**Where schema-per-tenant actually wins** and we would reconsider:
- Regulated environments with hard physical-separation requirements (HIPAA covered entities, PCI merchants) where a compliance auditor wants to see a DB-level boundary, not a WHERE clause.
- Capacity planning per tenant (one noisy tenant = one noisy schema, easier to isolate).
- Data-portability guarantees that look like `pg_dump --schema=tenant_123` on request.

Those tradeoffs don't match the target audience of this starter (small-to-medium SaaS). Row-level is the right default; the strict guard is what makes it safe.

## References

- `apps/core/models/tenancy.py` — the `TenantScopedQuerySet` guard.
- `tests/isolation/test_endpoint_isolation.py` — the matrix that proves cross-tenant endpoints return 404 across every operation.
- [`django-tenants` project](https://django-tenants.readthedocs.io/) — the schema-per-tenant library this ADR declines to use.
- ADR 003 — how unscoped queries are prevented.
- ADR 005 — 404 (not 403) for cross-tenant access.
