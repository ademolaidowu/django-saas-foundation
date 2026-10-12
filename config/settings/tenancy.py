"""
Tenant isolation guard configuration.

`TENANT_GUARD_ENABLED = False` disables the guard entirely (not recommended
outside of migrations or data-fix scripts — prefer `.unsafe_all()` for scoped
opt-outs).

`TENANT_GUARD_MODE` controls behavior when a `TenantScopedQuerySet` is
evaluated without `.for_organization(org)` or `.unsafe_all()`:
    "strict" → raise core.exceptions.UnscopedQueryError
    "warn"   → emit a RuntimeWarning
"""

TENANT_GUARD_ENABLED = True
TENANT_GUARD_MODE = env("TENANT_GUARD_MODE", default="strict")
