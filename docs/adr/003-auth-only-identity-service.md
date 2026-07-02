# ADR-003: Auth-only identity service; HR domain separated

Date: 2026-07-02 · Status: Accepted

## Context

The legacy backend bundled identity (`accounts`) with three HR business
domains (`hr`, `reviews`, `wellbeing`). Every other platform module is
a business service that trusts JWTs; keeping HR domains glued to auth
would make them privileged insiders bypassing the platform's own rules.

## Decision

`smarthr360-auth` owns exclusively: users, roles, groups, credentials,
token issuing, login security. Everything else — employee profiles,
skills, reviews, goals, wellbeing — moved to `smarthr360-core-hr`, a
peer service with its own database.

## Consequences

- Uniform architecture: auth has exactly one job; all business
  services authenticate the same way.
- Cost: User ForeignKeys in HR domains were replaced by `user_id`
  values + denormalized identity snapshots (see ADR-005), and profile
  creation is triggered lazily from token claims.
