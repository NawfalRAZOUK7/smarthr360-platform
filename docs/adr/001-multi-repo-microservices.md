# ADR-001: Multi-repo microservices architecture

Date: 2026-07-02 · Status: Accepted

## Context

SmartHR360 was developed by a team inside one shared repository that
grew into a coupled monolith: standalone projects were copy-pasted in
(`auth/`, `prediction_skills/`), drifted from their source repos, and
settings imported code across module boundaries. The functional spec
(cahier des charges, NFR "Scalabilité") explicitly requires a
microservices architecture with Docker containers.

## Decision

One repository per service under `github.com/NawfalRAZOUK7`:
`smarthr360-auth`, `smarthr360-core-hr`, `smarthr360_m3_future_skills`,
`smarthr360-career-sim` (v1); `smarthr360-workload`,
`smarthr360-policy-gen`, `smarthr360-retention` (v1.5); plus this
umbrella repo. Services communicate over HTTP/REST only.

## Consequences

- Teams work independently per repo; integration happens in the
  umbrella at pinned versions.
- No shared code except the published `smarthr360-jwt-auth` package.
- The legacy shared repo becomes read-only reference.
- More repos to maintain: mitigated by a standard CI template and a
  common repo layout (config/, Dockerfile, healthz, .env.example).
