# SmartHR360 — Reality Map & Architecture

The single source of truth for **what this system actually is** — grounded in the
code, not the pitch. Use it for the README, the defense, and to plan work
without contradicting the implementation.

> Legend for each capability: **[real]** verified in code and running,
> **[data]** a model/schema exists but isn't surfaced as a feature yet,
> **[planned]** described in the vision but not built.

---

## 1. Vision & objectives

SmartHR360 is a **satellite HR-analytics platform** that sits beside a heavy
central ERP (SAP / Odoo). Where the ERP is the system of record but rigid to
analyse, SmartHR360 adds three things:

1. **Interoperability** — ingest data from the ERP and re-expose it in an open,
   standard shape (HR-Open) so other systems can consume it.
2. **HR decision support (analytics + AI)** — turn raw employee data into live
   signals: who might leave, where skills are missing, who is burning out.
3. **Agility** — a light, fast web app for employees/managers/HR, with the
   heavy data synced from the ERP in the background.

## 2. System architecture

- **8 containers**: 7 Django/DRF microservices + 1 Next.js 16 frontend.
- **Per-service PostgreSQL** database (true isolation — no shared schema).
- **Central RS256 JWT auth**: the `auth` service holds the *private* signing
  key; every satellite verifies with the *public* key via JWKS. A compromised
  satellite can verify tokens but cannot forge them. **[real]**
- **Self-monitoring built in**: Prometheus scrapes all 7 services at `/metrics`
  (django-prometheus) **plus rich custom business metrics** — ERP-sync
  runs/records, skill-gap counts, workload burnout-risk, retention attrition
  risk, career/policy simulation counters, and auth failed-logins. Grafana
  provisions a **business dashboard** (all of these) + a **technical dashboard**
  (up/latency/5xx), and alert rules cover availability / 5xx / latency.
  Metrics use an idempotent `smarthr360_integration.observability` factory
  (`smarthr360_<subsystem>_<unit>`). Gunicorn runs multiple workers per service,
  so **Prometheus multiprocess aggregation** is enabled
  (`PROMETHEUS_MULTIPROC_DIR` + a shared `deploy/gunicorn.conf.py` with a
  `child_exit` hook; counters summed, gauges combined via `multiprocess_mode`)
  — a single event is counted correctly and visible on the next scrape. **[real]**
- **Orchestration**: one `docker-compose.yml`; one-command `bootstrap.sh`.

## 3. Cross-cutting foundations

| Foundation | Status | Where |
|---|---|---|
| **RS256 / JWKS auth** (asymmetric, central signer) | **[real]** | 6 services via the shared `smarthr360_jwt_auth` package; future-skills via its own `HybridJWTAuthentication` (same RS256/JWKS result) |
| **RBAC** (Employee / Manager / HR / Admin) | **[real]** | enforced backend (permissions) *and* frontend (RoleGate + nav locks) |
| **2FA (TOTP)** step-up | **[real]** | `auth`: `/2fa/setup`, `/activate`, `/disable` |
| **SCD Type 2 historisation** | **[real]** | `core-hr`: `date_fin` / `is_current`, "at most one open row per employee"; salary + department changes historized |
| **HR-Open interoperability export** | **[real]** | `core-hr`: `/interop/competency-definitions`, `/person-competencies`, `/position-competency-models` |
| **ERP ingestion** | **[real]** | `core-hr`: `sync_erp` + `import_employees` management commands, upsert logic |

## 4. Per-service reality

### auth (:8000) — identity & access
- **[real]** login (email/username), JWT RS256 issue/refresh/logout, register
  (self-service), password reset, change password, **2FA TOTP**, RBAC roles,
  user & role management (`/users`, `/users/<id>/role`), **GDPR self-erasure**
  (`/me/erase`).
- **Narrative correction:** this is **not** LDAP / Active Directory / SSO. The
  real, stronger story is **asymmetric RS256 + JWKS + 2FA**. Use that.

### core-hr (:8001) — the backbone (system of record)
- **[real]** employees CRUD + `/me` + `/my-team` + CSV export, departments,
  skills catalog, employee-skills, **skill-matrix heatmap**, org-chart,
  wellbeing surveys, performance reviews (cycles, items, goals, 360 feedback),
  **ERP sync**, **SCD2 history**, **HR-Open interop**.
- The richest service alongside future-skills.

### future-skills (:8004) — GPEC / skills intelligence
- **[real]** ML skill-demand predictions, market trends, HR investment
  recommendations, **model training pipeline** (RandomForest, ~0.986 acc),
  bulk-predict, **bulk employee import (+auto-predict)**, economic indicators,
  **service health/metrics monitoring**. Versioned API (v1/v2), own envelope
  renderer, own `HybridJWTAuthentication`.
- Most mature service (~272 test functions).

### retention (:8007) — churn prediction (ML brain)
- **[real]** attrition prediction, **run detection**, retention **conversations**
  (multi-turn chatbot), **actions** workflow (approve/reject/complete + record
  outcome), outcome stats, signal ingestion, **CSV export** of the latest
  attrition forecast.

### workload (:8005) — capacity & burnout
- **[real]** team burnout forecast, per-employee score + trend, **compute
  score**, daily **signals**, **rebalancing** suggestions, team overview,
  burnout alerts + acknowledge, **CSV export** of the team workload report.

### career-sim (:8003) — career-path simulator
- **[real]** positions catalog, **my profile**, cross-service **skills-gap**
  vs a target, **trajectory simulation** (readiness %, years-to-ready, 1/3/5y
  milestones), **multi-target compare**, **simulation history**.
- **Narrative correction:** it's an **employee-facing career-path simulator**,
  not "succession planning" (manager-replacement). Adjacent, not identical.

### policy-gen (:8006) — HR policy impact simulator
- **[real]** A/B **policy comparison** (salary increase, remote work, training
  budget, wellness, flexible hours, mentorship → predicted turnover /
  performance / cost), single **simulate**, **apply**, **optimize** (budget),
  **AI recommendations** (Groq), analytics KPIs, simulation history.
- **[real]** **PDF document generation** — employment contracts per employee
  (`/api/policy/employees/<id>/contract/`) and internal HR policy documents
  (`/api/policy/documents/policy/?policy_type=…`), rendered with reportlab from
  the `Employe`/`Contract`/`Salary` models; downloadable from the frontend
  **Documents** tab (HR-gated).
- **[data]** rich models: `Contract`, `Salary`, `Training`, `PerformanceReview`,
  `Employe`, `Skill` — feed both the simulation and the documents.
- Note: the core of the service is a **policy-impact simulator / optimizer**;
  the document generator is a complementary capability (so the name is now
  literally true).

## 5. Frontend

Next.js 16 (App Router, Turbopack), React 19, Tailwind v4, Recharts. Every one
of the 7 services has **read screens and write actions** wired to the real
backend, dark/light theming, mobile nav, RBAC front-to-back. See
`smarthr360-frontend/COVERAGE.md` (17 Playwright E2E tests, all green).

## 6. Honest gaps / roadmap

- **Custom business metrics** — **[done]** across the platform: every service
  emits domain metrics (ERP sync, skill gaps, burnout, attrition, career/policy
  sims) and they're wired into the Grafana business dashboard. Auth security
  metrics (`smarthr360_auth_failed_logins_total` by reason) were the one gap,
  now added with a dashboard security panel. A remaining *nice-to-have* is
  latency histograms (ERP-sync duration, ML inference time).
- ~~policy-gen PDF document generation~~ — **[done]** contracts + policy PDFs
  via reportlab, with a frontend Documents tab.
- **Thin-service depth** — deepened: career-sim (+compare/history tests),
  policy-gen (+PDF docs & tests), workload & retention (+CSV export & tests).
  Still lighter on tests than core-hr/future-skills, but each now has a real
  reporting/output capability.
- **Production hardening** — see `deploy/HARDENING.md` (production settings,
  HSTS, Alertmanager receiver).
- **Alertmanager** — **[done]** wired into compose; Prometheus routes firing
  alerts to it. Local receiver drops notifications (add Slack/email for prod).

## 7. The "master stroke": self-monitoring

Because Prometheus + Grafana are **inside** the same compose stack, SmartHR360
monitors *itself* — the ERP-sync speed of core-hr, the auth request/error
rates, the retention ML latency. That's what makes it read as a
**production-grade, self-observing ecosystem**, not a bag of separate demos.
