# django-saas-foundation

[![CI](https://github.com/ademolaidowu/django-saas-foundation/actions/workflows/ci.yml/badge.svg)](https://github.com/ademolaidowu/django-saas-foundation/actions/workflows/ci.yml)
![coverage](https://img.shields.io/badge/coverage-%E2%89%A585%25-brightgreen)
![python](https://img.shields.io/badge/python-3.12-blue)
![license](https://img.shields.io/badge/license-MIT-blue)

A reusable Django SaaS foundation with multi-tenancy, account-scoped authentication, RBAC, audit trails, and tenant-isolated APIs.

## Quickstart

```bash
git clone https://github.com/ademolaidowu/django-saas-foundation.git
cd django-saas-foundation
cp .env.example .env
make up
```

The stack boots in ~30 seconds. Then:

- Swagger UI: <http://localhost:8000/api/docs/>
- Admin: <http://localhost:8000/admin/>
- Health: <http://localhost:8000/api/health/>

### Demo logins

The compose boot runs `seed_demo` by default (`SEED_DEMO=true`). Password for all four demo users is **`demopass123`**.

| Email | Organization | Role |
|---|---|---|
| `alice@acme.com` | Acme Corporation | Owner |
| `bob@acme.com` | Acme Corporation | Member |
| `carol@acme.com` | Acme Corporation | Viewer |
| `dave@both.com` | Globex Innovations (primary) + Acme (secondary) | Owner on Globex, Member on Acme |

Register a fresh account instead via `POST /api/auth/register/`.

### Common commands

```bash
make help         # list every target
make up           # start stack
make down         # stop stack
make logs         # tail api logs
make test         # pytest + coverage
make lint         # ruff + format check
make typecheck    # mypy
make check        # Django system check + migrations consistency
make seed         # seed_rbac + seed_demo
```

## What's inside

- **Row-level multitenancy**: `TenantScopedQuerySet` refuses to evaluate until `.for_organization(org)` has been called. Cross-tenant access returns 404, not 403, so existence isn't leaked. See `docs/decisions/003-unscoped-query-prevention.md`.
- **Account-scoped tokens**: Knox tokens bind to an `Account`, not a `User`. An account has exactly one organization, so a token physically cannot be re-aimed. Switching orgs is a token rotation (`/api/auth/switch-organization/`). See `docs/decisions/002-account-scoped-tokens.md`.
- **Public UUIDs alongside integer PKs**: `public_id` (UUIDv7) is the external identifier; `id` stays integer for internal joins. See `docs/decisions/004-public-uuids-alongside-integer-pks.md`.
- **RBAC**: four seeded system roles per org (Owner/Admin/Member/Viewer) + custom roles. `@require_permission("code")` gates every endpoint. Last-Owner removal is blocked at the service layer.
- **Audit trail**: `AuditTrailMixin` adds `created_by` / `modified_by` / `deleted_by`. `django-simple-history` tracks every change to Project, Task, Role, RoleAssignment with the acting user. `GET /api/projects/{id}/history/` exposes the diff.
- **Tests**: 235 passing, 97% coverage, 85% CI floor. Isolation matrix covers every tenant endpoint; permission matrix covers every role × endpoint cell. See `tests/isolation/` and `tests/access/test_permission_matrix.py`.

## Architecture pattern

Each app follows:

```
apps/<app>/
├── models/              fields, constraints, indexes
├── serializers/
│   ├── input/           request validation
│   └── output/          response shape
├── selectors.py         reads — always tenant-scoped
├── services.py          writes — business rules, atomic
├── policies.py          object-level authorization
├── views.py             thin — parse input, call service, serialize output
├── urls.py
├── constants.py
└── admin.py
```

Linked blog posts (the Advanced Django series this starter is a reference for):

- [Advanced Django: Models](https://www.ademolaidowu.com/blog/advanced-django-models)
- [Advanced Django: Querysets and Managers](https://www.ademolaidowu.com/blog/advanced-django-querysets)
- [Advanced Django: Selectors and Services](https://www.ademolaidowu.com/blog/advanced-django-selectors-services)
- [Advanced Django: Serializers](https://www.ademolaidowu.com/blog/advanced-django-serializers)
- [Advanced Django: Views and Permissions](https://www.ademolaidowu.com/blog/advanced-django-views-permissions)

## Design decisions

Full write-ups live in `docs/decisions/`:

- [002](docs/decisions/002-account-scoped-tokens.md) Account-scoped tokens, not user-scoped.
- [003](docs/decisions/003-unscoped-query-prevention.md) How unscoped queries are prevented.
- [004](docs/decisions/004-public-uuids-alongside-integer-pks.md) Public UUIDv7 alongside integer PKs.
- [005](docs/decisions/005-404-not-403-for-cross-tenant.md) 404 (not 403) for cross-tenant access.
- [006](docs/decisions/006-middleware-driven-history-user.md) Middleware-driven history-user attribution.

## License

MIT.
