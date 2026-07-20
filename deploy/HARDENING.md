# SmartHR360 — production hardening checklist

This records the platform's current security posture and the concrete steps
required before a public/production deployment. The local `docker compose`
stack is intentionally relaxed for plain-HTTP development; the items below are
what changes for production.

## Already in good shape

- **`DEBUG` defaults to `False`** in every service's `config/settings/base.py`;
  only `local.py` / `development.py` turn it on.
- **`ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`** are environment-driven with
  safe defaults (no wildcards). The only `CORS_ALLOW_ALL_ORIGINS = True` is in
  future-skills **development** settings, never production.
- **Gunicorn** (multi-worker) serves every Django service — no `runserver` in
  any image.
- **Secrets** are generated at bootstrap via `scripts/gen_secret.sh` (per
  service, random) and injected through `.env`; nothing is committed. RSA
  keys for JWT live under `keys/` and are mounted as compose secrets.
- **Per-service PostgreSQL databases** (isolation between services).
- **JWT is RS256** (asymmetric): the auth service signs, satellites verify via
  the public key / JWKS — a compromised satellite cannot mint tokens.
- **`production.py`** already sets `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE` to `True`.

## Must change before production

1. **Run every service on `config.settings.production`.** The compose file
   currently runs 6 of 7 services on `config.settings.base` (only future-skills
   uses `production`). `base` keeps secure-cookie / SSL-redirect **off** so the
   plain-HTTP local stack works. In production, set
   `DJANGO_SETTINGS_MODULE=config.settings.production` for auth, core-hr,
   career-sim, workload, policy-gen, and retention — behind TLS termination.

2. **Terminate TLS** at a reverse proxy (nginx / Traefik / cloud LB) in front
   of the gunicorn services and the frontend; never expose gunicorn directly.

3. **HSTS and framing protection** — **[done]** every service's `production.py`
   now sets `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`,
   `SECURE_HSTS_PRELOAD`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`,
   `SECURE_REFERRER_POLICY`, and `SECURE_PROXY_SSL_HEADER`. (Active only under
   production settings, i.e. behind the TLS proxy.)

4. **Tighten `CORS_ALLOWED_ORIGINS`** to the real frontend origin(s) only
   (currently `http://localhost:3100` for local).

5. **Restore strict throttles.** Local compose relaxes
   `THROTTLE_LOGIN` / `THROTTLE_REGISTER` to ease seeding. Production must use
   conservative rates (the DRF throttle classes are already wired).

6. **Database least privilege.** The app role should not own the schema or hold
   `CREATEDB`/superuser in production; grant only CRUD on its own database.
   Use a separate migration role for `manage.py migrate`.

7. **Secret rotation & storage.** Move `.env` secrets and the JWT keypair into
   a managed secret store (Vault, AWS/GCP Secrets Manager). Rotate the JWT
   signing key on a schedule; publish the public key via JWKS so satellites
   pick up rotation automatically.

8. **Grafana admin password.** `GRAFANA_PASSWORD` defaults to `admin` — set a
   strong value and disable anonymous access.

## Observability (added in this pass)

- **Alert rules** — `deploy/observability/alerts.rules.yml` (service down,
  flapping, high 5xx rate, sustained 5xx, p95 latency > 1s), loaded by
  `prometheus-compose.yml`.
- **Technical dashboard** — `grafana-smarthr360-technical.json` (per-service
  up status, request rate, 5xx rate, p95 latency, status-class mix).
- **Multiprocess metric aggregation** — enabled via `PROMETHEUS_MULTIPROC_DIR`
  + `deploy/gunicorn.conf.py` (`child_exit` hook) so custom counters/gauges are
  correct across all gunicorn workers (not per-worker). Gauges set
  `multiprocess_mode` (`livesum` for counts, `max` for timestamps).
- **Alertmanager** — **[done]** an `alertmanager` container is wired into
  compose, Prometheus routes firing alerts to it (`alerting:` block), and
  `alertmanager.yml` defines grouping + inhibition. The local receiver drops
  notifications (no dev creds) — alerts are visible at `localhost:9093`; add a
  Slack/email/PagerDuty receiver for production (commented example included).
- **Non-root containers** — **[done]** every service now runs gunicorn as an
  unprivileged `appuser` (`USER appuser` in each Dockerfile), so the Prometheus
  multiprocess dir and processes are no longer root-owned.

## Pre-deploy checklist

- [ ] `DJANGO_SETTINGS_MODULE=config.settings.production` on all services
- [ ] TLS in front of every service; `SECURE_PROXY_SSL_HEADER` set
- [x] HSTS + `X_FRAME_OPTIONS=DENY` + nosniff added to production settings
- [ ] `CORS_ALLOWED_ORIGINS` restricted to real frontend origin(s)
- [ ] Strict throttle rates restored
- [ ] DB app-role least privilege; migrations run as a separate role
- [ ] Secrets in a managed store; JWT key rotation scheduled
- [ ] Grafana admin password changed
- [x] Alertmanager wired (add a real receiver for prod)
- [x] Services run as non-root
- [ ] `docker compose config` clean; images scanned (e.g. Trivy) in CI
