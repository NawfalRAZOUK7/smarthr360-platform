# ADR-004: RS256 JWT with local verification

Date: 2026-07-02 · Status: Accepted

## Context

Services must authenticate requests issued on behalf of platform users
without sharing a database with auth. All repos are public on GitHub,
so any shared signing secret would be at permanent risk of exposure.

## Decision

`smarthr360-auth` signs tokens with an RS256 **private key** it alone
holds. Every other service verifies signatures **locally** with the
**public key** (safe to distribute/commit) via the shared
`smarthr360-jwt-auth` package — no network call to auth per request.
Access tokens are short-lived (15 min) and carry `user_id`, `email`,
`role`, `groups`, `is_superuser` claims; refresh tokens rotate with
blacklist.

## Alternatives considered

- **HS256 shared secret**: any holder can forge tokens; unfit for a
  public multi-repo project.
- **Introspection endpoint per request**: doubles every API call and
  makes auth a runtime single point of failure.

## Consequences

- Services stay up (for valid tokens) even if auth is briefly down.
- Revocation before expiry is limited to the refresh flow — accepted
  with the 15-minute access lifetime.
- Key distribution: `scripts/generate_rsa_keys.sh`; services may also
  fetch `GET /.well-known/jwt-public-key.pem` from auth at startup.
