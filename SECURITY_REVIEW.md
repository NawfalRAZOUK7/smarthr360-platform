# SmartHR360 — Security Review

Scope: the 7 Django/DRF services, the shared JWT package, the Next.js frontend, and
the deployment posture. This is a pre-production review; findings are rated
Critical / High / Medium / Low with current status.

## Summary

The platform's authn/authz foundation is strong: RS256 JWT with JWKS rotation,
claim-based roles enforced server-side, row-level scoping, and a genuine separation
of duties (identity administration is ADMIN-only). The main residual risks are
operational: secret hygiene, public-demo abuse surfaces, and CORS/DEBUG configuration
that must be correct in production.

## Findings

| # | Sev | Area | Finding | Status / Recommendation |
|---|-----|------|---------|--------------------------|
| 1 | High | Secrets | The m3/future-skills module had secrets committed to history in the past. | **Action required**: rotate any historically exposed keys/tokens; confirm `.env`, `keys/*.pem` are git-ignored; add the gitleaks job (already in platform CI) as a required check. |
| 2 | High | Config | `DEBUG` must be `False` and `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` locked to the demo domain in production. | Enforced via `config.settings.production` + `.env.prod`. **Verify** no service falls back to `base`/`development` in the prod overlay. |
| 3 | Med | Availability | Future-skills bulk import historically ran a synchronous full-matrix ML recalculation → a slow/DoS-prone request. | **Resolved** by #49 (async predictions via Celery/threads; `FUTURE_SKILLS_ASYNC_PREDICT=1` on the public box). |
| 4 | Med | Abuse | Self-report endpoints (`retention /signals/ingest`, `retention /checkin`, notification ingest) can be spammed by an authenticated user about themselves. | Dedupe-on-open exists; add per-user rate limiting (DRF throttles) on these write endpoints for the public demo. |
| 5 | Med | Authz | Cross-service calls pass the caller's JWT through (`CoreHRClient` etc.). Correct, but a compromised service could replay tokens within their 15-min TTL. | Acceptable for the model; keep TTL short (already ~15 min) and services network-isolated behind Caddy (no public backend ports in prod overlay). |
| 6 | Low | Privacy | Wellbeing surveys are intentionally anonymous (no user link). The opt-in self check-in (#46) is a *separate*, consented channel. | **By design** — do not link survey responses to individuals. Documented. |
| 7 | Low | AuthN | django-axes lockout on repeated failed logins is enabled. | Good. Confirm lockout thresholds and that the audit log surfaces lockouts (it does, via `AuditLogView`). |
| 8 | Low | Injection | Search/filter endpoints use ORM `icontains`/`Q` (no raw SQL); inputs are DRF-validated. | No SQL-injection surface found. |
| 9 | Low | GDPR | Self-erasure and admin-erase **anonymize** rather than hard-delete (keeps cross-service `user_id` integrity) and blacklist tokens. | Good pattern; ensure anonymized emails can't collide. |
| 10 | Low | Frontend | `NEXT_PUBLIC_*` URLs are build-time public by nature; no secrets are shipped to the client. Tokens live in memory + refresh flow. | OK. Confirm no secret is placed in a `NEXT_PUBLIC_` var. |

## Authorization model (verified)

- **Roles**: EMPLOYEE / MANAGER / HR / ADMIN, plus AUDITOR & SUPPORT as read-only JWT groups.
- **Separation of duties**: user/role administration is ADMIN-only (`IsAdminRole`); HR owns people data but cannot assign roles or list accounts.
- **Row-level scoping**: managers see only their direct team (core-hr querysets + the workload team roster); employees see only themselves.
- **Read-only roles**: write controls are gated on `hasManagerAccess`/`hasHrAccess`/`hasAdminAccess`, which exclude AUDITOR/SUPPORT, so read-only falls out structurally.
- **Audit trail**: every role change is recorded (`RoleChange`) and surfaced with login-security events to ADMIN/AUDITOR.

## Public-demo hardening checklist

- [ ] Guest account is AUDITOR-group (read-only); confirm no write path is reachable.
- [ ] Backend service ports are **not** published (only Caddy 80/443) — enforced by the prod overlay.
- [ ] DRF throttles on auth + self-report endpoints.
- [ ] Rotate secrets; gitleaks required in CI.
- [ ] `DEBUG=False`, HSTS + secure headers on (Caddy + each service's `production.py`).
- [ ] Postgres not exposed to the internet; strong password from `.env.prod`.

## Residual / out of scope

Full DAST/pentest, dependency CVE audit (`pip-audit`/`npm audit` in CI is recommended
next), and formal threat modeling of the ERP/EAI ingestion path.
