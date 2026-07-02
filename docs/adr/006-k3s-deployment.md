# ADR-006: Kubernetes (k3s) deployment target

Date: 2026-07-02 · Status: Accepted

## Context

The platform (4 services in v1, 7+ in v1.5, plus Postgres and
monitoring) needs a public deployment. Options evaluated: managed PaaS
(Railway/Render), VPS with docker compose, VPS with k3s.

## Decision

Deploy on a single VPS (≥4 GB RAM) running **k3s** (lightweight
Kubernetes): one Deployment/Service per microservice, Ingress with TLS
(cert-manager/Let's Encrypt), Secrets for keys and passwords, Postgres
via StatefulSet or managed add-on. Manifests live in this repo under
`deploy/k3s/`.

## Consequences

- Strongest operational learning outcome and portfolio signal
  (orchestration, ingress, secrets, probes, rollouts).
- Higher initial setup cost than compose — accepted deliberately.
- docker-compose remains the local development path; parity between
  compose services and k8s manifests must be maintained.
