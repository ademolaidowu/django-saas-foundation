# ADR 004 — Public UUIDs alongside integer primary keys

**Status:** Accepted
**Phase:** 1 (Core and tenancy)

## Context

Every row needs two kinds of identifier:
- An internal one for joins, indexing, and FK integrity — small, dense, fast.
- An external one for URLs, API payloads, and anywhere a client sees it — unguessable, non-sequential, portable across systems.

Options:
1. **Integer PK only.** Fastest joins, cheapest storage. But `GET /projects/42` leaks row count ("42 projects exist") and enumeration risk ("let me try /projects/43"). Hard to merge rows across databases later.
2. **UUID PK only.** Opaque, portable, but UUIDv4 is random — insert pathology on B-tree PKs (page splits everywhere) and 16 bytes per FK adds up at scale.
3. **Both — integer PK for internal use, UUID surrogate for external.** Pay the extra column cost; keep hot joins integer-fast.

## Decision

`BaseModel` carries both:

- `id = BigAutoField(primary_key=True)` — internal only. Never serialized, never in URLs, never in error messages.
- `public_id = UUIDField(unique=True, db_index=True, default=uuid7, editable=False)` — the external identifier. API routes use it (`/api/projects/{public_id}/`), serializers expose it as `id` to clients, loggers reference it.

UUIDs are **version 7** via the `uuid-utils` package. UUIDv7 encodes a millisecond timestamp in its leading bits, so new rows cluster at the end of the B-tree index — same locality benefits as a sequential integer, with the opacity of a UUID. UUIDv4 would thrash the index with random inserts.

## Consequences

- **URLs.** Routers use a `<uuid:public_id>` path converter against the `public_id` column — not `pk`.
- **Serializers.** Output serializers rename `public_id` to `id` with `serializers.UUIDField(source="public_id", read_only=True)` so clients see a stable `id` key without the internal integer leaking.
- **FKs stay integer.** `ForeignKey(Project)` still binds `project_id BIGINT`. Only the external surface uses the UUID.
- **Storage.** Every row costs 16 extra bytes for `public_id` plus the unique index. Acceptable at the scale this repo targets.
- **Shell / debugging.** `.get(pk=42)` works in the shell. Logs include `public_id` so you can grep across environments.
- **Admin.** Register `public_id` as readonly. Internal `id` stays visible in the detail URL (admin uses pk by default) — fine, admin isn't a public surface.

## Alternatives considered

- **UUIDv4.** Rejected — random inserts are the single largest B-tree write-amplification source in Postgres. Measurable throughput loss on bulk writes.
- **ULID.** Comparable to UUIDv7 (timestamp-prefixed) but Django's `UUIDField` validates against RFC 4122 formatting. UUIDv7 is spec-compliant and library-supported.
- **Prefix-encoded public IDs (`prj_01HFT…`).** Nicer in logs, but requires custom encode/decode and gives up `UUIDField`'s database-level typing. Not worth the custom code for Phase 1.

## References

- `apps/core/models/base.py` — the `uuid7()` helper and the `public_id` field
- [uuid-utils](https://pypi.org/project/uuid-utils/) — provides a `uuid7()` generator
- [RFC 9562 §5.7](https://www.rfc-editor.org/rfc/rfc9562#name-uuid-version-7) — UUIDv7 specification
