## Context

You are building `django-saas-foundation`, a public, open source Django REST backend that shows how to build a production grade multitenant SaaS foundation. It is a portfolio repository: the code will be read by senior engineers and hiring managers, so clarity and correctness matter more than feature count.

The author writes the "Advanced Django" blog series (models, querysets and managers, selectors and services, input and output serializers, views and permissions). This repository is the working reference for those patterns. Follow them exactly as described below.

Build everything from scratch. Do not import code from any other project.
Reference the following projects and let me know if there are any questions:
/Users/mac/Organizations/Sonecare/sonecare-api
/Users/mac/Organizations/Ampstem/sparkle-commerce-api

## Hard rules

1. **Tenant isolation is the point of the repo.** No query may return another organization's rows. Every tenant scoped model goes through a tenant aware manager, and every endpoint is covered by an isolation test.
2. **Small scope, finished well.** Implement only what this spec lists. Put anything else under "Roadmap" in the README.
3. **Readable over clever.** Plain functions in services and selectors, explicit names, type hints everywhere, short docstrings explaining _why_, not _what_.
4. **Ask before deviating.** If a rule here conflicts with something you think is better, stop and explain the tradeoff instead of silently changing it.
5. Work in the phases below. After each phase, run the tests and linters, then summarise what changed before moving on.

## Stack

- Python 3.12, Django 5.x, Django REST Framework
- PostgreSQL 16, Redis 7 (cache only for now)
- `django-rest-knox` for tokens, `drf-spectacular` for OpenAPI, `django-simple-history` for audit, `django-environ`, `django-split-settings`
- `uv` for dependencies, Ruff (lint and format), mypy with `django-stubs` and `djangorestframework-stubs`, pre-commit
- pytest, pytest-django, model-bakery (or factory_boy), pytest-cov
- Docker (multistage), docker compose, GitHub Actions

## Repository layout

```
django-multitenant-starter/
├── apps/
│   ├── core/            # BaseModel, tenant managers, middleware, response format, exceptions, pagination
│   ├── tenants/         # Organization
│   ├── accounts/        # User, Account (User × Organization), AccountToken, auth endpoints
│   ├── access/          # Permission registry, Role, RoleAssignment, @require_permission, policies
│   └── projects/        # Example domain: Project, Task
├── config/
│   ├── settings/        # split settings: base, local, test, production
│   ├── urls.py
│   ├── asgi.py / wsgi.py
├── docs/
│   ├── architecture.md
│   └── decisions/       # ADRs, one file per decision
├── tests/               # mirrors apps/
├── entrypoint.sh
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```

Each app follows this structure:

```
apps/<app>/
  models/            # fields, constraints, indexes; no business logic
  serializers/
    input/           # request validation (plain Serializer)
    output/          # response shape (ModelSerializer)
  selectors.py       # read operations, always tenant scoped
  services.py        # write operations and business rules, wrapped in transactions
  policies.py        # object level authorization
  views.py           # thin: parse input, call service or selector, serialize output
  urls.py
  constants.py       # enums and choices
```

## Phase 1: Core and tenancy

- `core.BaseModel` (abstract): internal `BigAutoField` `id`; public `public_id` (UUIDv7, exposed in the API instead of `id`); `source` (`RecordSource` enum: api / admin / import / system / integration / migration / seed); `created_at`, `modified_at`, `deleted_at`. `objects` returns all rows (including soft deleted); `records` returns alive rows only. `is_deleted()` is a method; `delete()` is a soft delete; `hard_delete()` escapes.
- `core.AuditTrailMixin` (abstract, **separate** from `BaseModel`): adds `created_by` (NOT NULL, `on_delete=PROTECT`), `modified_by`, `deleted_by` (both nullable, PROTECT) user FKs, all with `related_name="+"`. Overrides `delete(deleted_by=...)` to require the actor. Compose with `BaseModel` only on human-driven rows (e.g. `class Project(AuditTrailMixin, BaseModel)`). System-written rows (tokens, notifications) skip it. Actor is captured explicitly via a service-method kwarg — no middleware, no thread-local, no signals.
- `tenants.Organization`: name, unique slug, `is_active`.
- `core.TenantScopedModel` (abstract, extends `BaseModel`): `organization` foreign key (PROTECT). Default managers (`objects`, `records`) use a `TenantScopedQuerySet` whose querysets must be filtered with `.for_organization(org)` and otherwise refuse to evaluate — raising `UnscopedQueryError` in strict mode, warning in warn mode. Document the mechanism in ADR 003. `.unsafe_all()` is the explicit opt-out for admin, migrations, and fix-scripts.
- Standard response envelope and error format via a renderer and exception handler, for example `{"data": ..., "meta": ...}` and `{"error": {"code": ..., "message": ..., "request_id": ..., "fields": ...}}`.
- Pagination class with `page` and `page_size`.

## Phase 2: Accounts and authentication

- Custom `User` (email login, no username).
- `Account`: links a User to an Organization with a status (invited, active, suspended). One user can hold accounts in several organizations.
- `AccountToken`: Knox token tied to a specific Account, so a token carries the organization context. A custom authentication class resolves `request.user`, `request.account` and `request.organization` from the token.
- Endpoints: register (creates user, organization and owner account), login (returns a token per chosen organization), logout, `GET /me`, list my organizations, switch organization (issues a token for another account).
- Cross organization rule: a token for Account A can never act on Organization B, even if the user also belongs to B.

## Phase 3: Access control (RBAC)

- `Permission` registry: codename (for example `projects.create`), module, description. Seeded by an idempotent `seed_rbac` management command from a single Python definition file.
- `Role`: per organization, with a name, a set of permissions, and an `is_system` flag for seeded defaults (Owner, Admin, Member, Viewer).
- `RoleAssignment`: Account to Role.
- `@require_permission("projects.create")` decorator for views, and object level checks in `policies.py` (for example, only the task assignee or an admin can close a task).
- Endpoints to list permissions, CRUD custom roles, and assign roles to accounts. Owners cannot remove the last Owner.

## Phase 4: Example domain and audit

- `projects.Project` (name, description, status) and `projects.Task` (project, title, status, assignee Account, due date), both tenant scoped.
- Full CRUD through the layered structure, filtering by status, and permission checks on every endpoint.
- `django-simple-history` on Project, Task, Role and RoleAssignment. History records the acting user via middleware. Set `SIMPLE_HISTORY_REVERT_DISABLED = True`. Expose `GET /projects/{uuid}/history`.
- `seed_demo` management command: two organizations, several users (one belonging to both), roles, and sample projects and tasks. Idempotent.

## Phase 5: Tests

This is the most important phase.

- **Isolation suite:** a parametrised test that, for every tenant scoped endpoint (list, retrieve, update, delete, history), authenticates as a member of Org A and confirms Org B's objects return 404 (not 403, so existence is not leaked) and never appear in lists.
- Token switching: a user in both orgs cannot use Org A's token on Org B data.
- RBAC: each seeded role gets exactly the expected allowed and denied actions; custom roles work; last Owner protection works.
- Audit: changes create history rows with the right user.
- Services and selectors unit tested directly, not only through the API.
- Target 90%+ coverage on `apps/`. Fail CI below 85%.

## Phase 6: Delivery

- **Dockerfile:** multistage (builder with uv, slim runtime), non root user, healthcheck.
- **docker-compose.yml:** api, postgres, redis, with healthchecks and a named volume.
- **entrypoint.sh** (Bash, `set -euo pipefail`): wait for Postgres, run migrations, run `seed_rbac`, optionally `seed_demo` when `SEED_DEMO=true`, then start Gunicorn. Log each step.
- **Makefile:** `up`, `down`, `test`, `lint`, `typecheck`, `migrate`, `seed`, `shell`, `logs`.
- **pre-commit:** Ruff, Ruff format, mypy, end of file and trailing whitespace fixers.
- **GitHub Actions:** on push and pull request: uv sync, Ruff, mypy, `makemigrations --check`, pytest with coverage against a Postgres service container, upload coverage summary. Add the status and coverage badges to the README.
- Swagger UI at `/api/docs/`, schema at `/api/schema/`.

## Phase 7: Documentation

**README.md**, in this order:

1. One line description and badges.
2. Why this exists (two sentences).
3. Quickstart: `git clone`, `cp .env.example .env`, `make up`, then the URLs and demo logins.
4. Architecture: a Mermaid diagram of the request lifecycle (token → AccountToken → Account → Organization → permission check → selector or service → tenant scoped query), and a second Mermaid ER diagram of the core models.
5. How tenant isolation is enforced (the layers, in plain words).
6. How RBAC works, with an example of adding a new permission.
7. Project structure and the layered app pattern, linking to the Advanced Django posts:
   - https://www.ademolaidowu.com/blog/advanced-django-models
   - https://www.ademolaidowu.com/blog/advanced-django-querysets
   - https://www.ademolaidowu.com/blog/advanced-django-selectors-services
   - https://www.ademolaidowu.com/blog/advanced-django-serializers
   - https://www.ademolaidowu.com/blog/advanced-django-views-permissions
8. Design decisions, linking to the ADRs.
9. Roadmap.
10. License (MIT).

**ADRs** in `docs/decisions/`, short (context, decision, consequences):

- 001 Row level tenancy instead of a schema per tenant (compare with django-tenants: migrations, connection pooling, cross tenant reporting, operational cost).
- 002 Account scoped tokens instead of user scoped tokens.
- 003 How unscoped queries are prevented.
- 004 Public UUIDs alongside integer primary keys.
- 005 404 instead of 403 for cross tenant access.

**docs/architecture.md:** a longer walkthrough of the request lifecycle and where each check happens.

## Roadmap (do not build; list in README)

Subscription billing, invitations by email, SSO (OIDC), Celery background jobs, rate limiting, a React admin frontend, per tenant feature flags.

## Definition of done

- `make up` on a clean machine starts everything; seeded demo data and Swagger docs are reachable.
- `make test`, `make lint` and `make typecheck` pass locally; CI is green.
- The isolation suite covers every tenant scoped endpoint.
- README renders correctly on GitHub, including both Mermaid diagrams.
- No secrets in the repository; `.env.example` documents every variable.

When everything is done, give me a short summary of the architecture and a list of the five design decisions most likely to come up in an interview, with a one paragraph explanation of each.
