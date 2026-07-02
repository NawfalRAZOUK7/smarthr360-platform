# ADR-002: Umbrella repo with pinned submodules + compose

Date: 2026-07-02 · Status: Accepted

## Context

With one repo per service we need a reproducible way to define "the
platform" — which versions of which services work together — without
requiring CI/CD infrastructure on day one.

## Decision

This repo (`smarthr360`) contains no application code. It holds:
git submodules pinning each service at an exact commit,
`docker-compose.yml` for local development, Kubernetes (k3s) manifests
for deployment, the shared `smarthr360-jwt-auth` package, ADRs and
platform documentation.

Daily development happens in service repos. The umbrella is updated at
integration time by bumping submodule pointers (one commit = one
platform state).

## Alternatives considered

- **Compose-only pulling GHCR images**: cleaner but requires CI +
  registry on every repo before anything runs; planned as evolution.
- **Docs + clone script**: no version pinning — the drift that broke
  the legacy shared repo would return.

## Consequences

- `git clone --recursive` yields the entire platform at known-good
  versions.
- Contributors must learn two submodule commands; documented in README.
