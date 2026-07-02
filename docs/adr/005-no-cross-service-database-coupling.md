# ADR-005: No cross-service database coupling

Date: 2026-07-02 · Status: Accepted

## Context

In the legacy monolith, HR-domain tables had ForeignKeys to the auth
User table and code imported auth helpers that queried the database.
Any service split leaves such references dangling.

## Decision

Each service owns a private database (one Postgres instance, separate
databases). Cross-service references are **by value**:

- users appear in business services only as `user_id` (+ optional
  denormalized snapshots such as email/name/role refreshed from token
  claims);
- role checks are evaluated from JWT claims via `smarthr360_jwt_auth`,
  never by querying auth;
- services needing rich identity data call auth's REST API.

Two implementation patterns are sanctioned:

1. **Plain user_id fields** (used by core-hr) — cleanest for new code.
2. **Local identity projection** (used by career-sim, transitional) —
   a local user table whose primary keys mirror auth user ids,
   populated lazily from claims, preserving existing FKs during
   migration.

## Consequences

- Independent deploys, migrations and backups per service.
- Eventual consistency of denormalized snapshots is accepted; the
  token is always the authoritative source at request time.
