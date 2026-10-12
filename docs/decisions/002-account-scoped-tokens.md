# ADR 002 — Account-scoped tokens instead of user-scoped tokens

**Status:** Accepted
**Phase:** 2 (Accounts and authentication)

## Context

A user may belong to several organizations in this system — a consultant on three client orgs, an employee who is also a side-project owner, a staff user with their own personal workspace. Every authenticated request has to answer one question: *which organization is this user acting on right now?*

The lazy answer is "put the organization in the request" — a header, a URL prefix, or a query param. All three are client-controlled. The user picks the org, the server trusts the pick. One typo or one malicious client, and the server executes a mutation against the wrong tenant with a legitimate token.

The alternative is to encode the org in the token itself. The server derives the org from the token; the client never names it. A token that was minted for Account A on Org Alpha physically cannot be re-aimed at Org Bravo, even by the same user who also belongs to Bravo — the client would have to log in again, be issued a different token, and the two tokens are distinct rows in two distinct chains.

## Decision

Tokens bind to an **Account**, not a **User**. An Account has exactly one Organization. The authentication class derives `request.user`, `request.account`, and `request.organization` from the token chain on every request:

```
Knox AuthToken  ──1:1──▶  AccountToken  ──FK──▶  Account  ──FK──▶  Organization
```

Concretely:
- `knox.AuthToken` provides the token digest + user. Standard Knox.
- `accounts.AccountToken` is a bare join row (OneToOne to AuthToken, FK to Account) created in the same transaction as the AuthToken.
- `accounts.authentication.AccountTokenAuthentication` loads the entire chain in one `select_related` and attaches `request.account` + `request.organization` before the view runs.
- The chain is reconstructed on every request; nothing is trusted from the client beyond the raw token itself.
- `/switch-organization/` destroys the current token and mints a new one for a different account — token rotation is the mechanism for changing orgs.

## Consequences

**What this buys:**
- Impossible-by-construction cross-org access with a stolen or stale token. A token can only touch the org it was minted for.
- Deactivation is instant: setting `account.status != ACTIVE` makes every outstanding token for that account fail on the next request. No "pending revocation" window.
- The transport is irrelevant. Cookie, Authorization header, mobile, web — all share the same backend. "Which org?" is answered the same way everywhere.
- Audit logs are honest: `request.account` tells you exactly who did what in which org, not just which user.

**What this costs:**
- A user with memberships in N orgs needs N tokens over time (sequentially, one at a time per client). The frontend can cache multiple tokens if it wants parallelism, but the server never shares a token across orgs.
- One extra row per login (`AccountToken`) and one extra `select_related` hop on every authenticated request. Measured overhead: a single JOIN; one network round-trip to Postgres.
- Switching orgs is a server round-trip, not a client-side flag. Acceptable for a REST backend — the trade-off is the whole point.

**Trade-offs considered and rejected:**
- *Put the org in the URL (`/api/orgs/<slug>/projects/`).* Beautiful for routing, lethal for security. The client picks the slug; the server trusts it. We'd need an explicit "is this user allowed in this org?" check on every request, and one missing check anywhere leaks data.
- *Put the org in a header (`X-Organization-Id`).* Same problem as the URL, with less structure.
- *User-scoped tokens + an "active org" column on User.* Looks simple until two tabs are open in different orgs; the row flips under both of them and whichever request lands second clobbers the first. Also makes `switch-organization` racy.
- *JWT with org claim.* Fine until you need to deactivate: JWTs are stateless, so revocation requires a side-channel (deny-list, short TTL, refresh dance). Knox + a database row gives us immediate revocation for free.

## Enforcement in code

- `apps/accounts/cookies.py:return_response_with_auth_cookie` — creates both `AuthToken` and `AccountToken` atomically on every login/register/switch.
- `apps/accounts/authentication.py:AccountTokenAuthentication._attach_request_context` — reads the chain on every request, rejects if any link is missing, rejects if `account.status != ACTIVE`.
- `tests/accounts/test_token_isolation.py` — proves that:
  1. A token for Account A sees only Org Alpha's rows (TenantScopedQuerySet enforces it against `request.organization`).
  2. Switching to Account B issues a new token and invalidates the old one.
  3. If the `AccountToken` row is deleted (hypothetical tamper), auth fails cleanly.

## References

- `apps/accounts/models/token.py` — the `AccountToken` row.
- `apps/accounts/authentication.py` — the auth class.
- `docs/decisions/003-unscoped-query-prevention.md` — companion guarantee at the ORM layer.
