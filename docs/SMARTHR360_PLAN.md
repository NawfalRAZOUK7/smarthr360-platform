# SmartHR360 — Architecture, Migration & Release Plan

> Owner: Nawfal Razouk · Date: 2026-07-02 · Status: Approved for execution
> This document is the single reference for migrating SmartHR360 from the legacy shared repo to a clean multi-repo microservices platform under `github.com/NawfalRAZOUK7`, and for the v1 → v1.5 → v2 roadmap.

---

## 1. Context & Goals

SmartHR360 is a predictive HR platform (per the *Cahier des charges fonctionnel*): it shifts HR from reactive administration to prediction and prevention — mental workload monitoring, AI career simulation, future-skills forecasting, AI policy generation, and a retention chatbot.

The project was developed as a team inside the shared repo `majda2001/SmartHR360`, which became a coupled monolith with vendored copies of standalone repos. That repo is now **reference-only**. All future work happens in fresh repos under Nawfal's account.

**Portfolio goals** (LinkedIn / CV): demonstrate Software Engineering (microservice design, ADRs, clean APIs), DevOps (Docker, CI/CD, Kubernetes, monitoring), and Full-stack capability. The *quality and presentation* of the repos is a deliverable, not a side effect.

---

## 2. Decisions (agreed 2026-07-02)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Repo strategy | **Multi-repo microservices** — one repo per service | Matches original design (services on :8000/:8001/:8002), matches cahier des charges NFR ("architecture microservices"), best portfolio story |
| D2 | Umbrella repo | **`smarthr360`: git submodules (pinned) + docker-compose (dev) + k3s manifests (prod)** | Reproducible integration without CI prerequisites; daily dev stays in module repos |
| D3 | Auth scope | **Auth-only identity service**; hr + reviews + wellbeing move to a separate `core-hr` service | Uniform architecture: every business service is a peer that trusts JWT; identity does one job |
| D4 | Inter-service auth | **Local JWT verification, RS256** | Public key is committable to GitHub; no runtime dependency on auth; SimpleJWT supports it |
| D5 | Data isolation | **No shared DB, no cross-service ForeignKeys** — services know users only as `user_id` + role claims from the token | Core microservice rule; enables independent deploys |
| D6 | Git history | **Fresh, clean start** in all new repos; old repos archived as history | Committed secrets/sqlite/venv/node_modules must not carry over |
| D7 | Drift resolution | **Shared-repo copy of prediction_skills wins** — it is strictly ahead of the standalone m3 repo (verified by diff: one-directional) | Copy back into `smarthr360_m3_future_skills` as one commit, excluding junk |
| D8 | Deployment | **Kubernetes (k3s) on a VPS** (~4 GB RAM) | Maximum DevOps signal; umbrella carries manifests; compose remains for local dev |
| D9 | Frontend | **Deferred** until backend + APIs + infra are solid | Decided; tech choice (polish HTMX vs React) re-discussed at that point |
| D10 | Language | **English** for all READMEs, API docs, architecture docs; repo names in English | International reach |

---

## 3. Service Catalog (target state)

Legend for *State*: ✅ real code exists · 🔧 needs extraction/rework · 🏗️ needs building · 🛟 rescue from branch

### 3.1 `smarthr360-auth` — Identity service
- **Role**: the only service that knows passwords. Users, roles (Employee / Manager / HR / Admin), token issuing.
- **Source**: `accounts` app of `smarthr360_backend`. State: ✅🔧 (extract from backend repo)
- **Owns**: User, roles, login activity, verification/reset tokens. Signs JWT with **RS256 private key**.
- **Key APIs**: register, login, refresh, verify-email, password-reset, lockout handling, login-activity log, JWKS/public-key endpoint (`/.well-known/jwks.json`) for other services.

### 3.2 `smarthr360-core-hr` — Employee & organization service
- **Role**: system of record for people and how they're doing.
- **Source**: `hr` + `reviews` + `wellbeing` apps of `smarthr360_backend`. State: ✅🔧 (surgery: User FKs → `user_id`; profile creation triggered on registration)
- **Owns**: Department, EmployeeProfile, Skill, EmployeeSkill (proficiency levels), FutureCompetency; ReviewCycle, PerformanceReview (Draft→Submitted→Approved), ReviewItem, Goal; WellbeingSurvey, SurveyQuestion, SurveyResponse.
- **Key APIs**: profiles CRUD + search/filter, skills catalog, review workflow, goals, surveys.

### 3.3 `smarthr360_m3_future_skills` — Skills prediction service (Module 3)
- **Role**: ML forecasting of future skill demand. **The MLOps showcase.**
- **Source**: existing repo + reconciliation from shared copy (D7). State: ✅ (most advanced module; exceeds the rapport's description — code wins over docs)
- **Owns**: skill taxonomy (Industry / Domain / Function / SkillDomainMap, i18n), predictions, snapshots, drift reports.
- **Capabilities**: ML pipeline, MLflow tracking, drift monitoring, Celery async tasks, evaluation dashboards, catalog loader, Prometheus/Grafana monitoring.

### 3.4 `smarthr360-career-sim` — Career simulation service (Module 2)
- **Role**: AI career trajectory modelling: current skills + history + aspirations + open positions → scenarios with success probabilities and training recommendations (1/3/5-year views).
- **Source**: `simulateur_parcours` (~4,700 lines) from shared repo. State: ✅🔧 (replace its `CustomUser` with token identity; DRF-ify)
- **Owns**: PosteCible, trajectories, certifications, training history/recommendations, mentorship, career plans.
- **Flagship v1 feature**: **Skills-gap endpoint** — given `user_id` + target position: pull current skills (core-hr) + demand predictions (future-skills) → return gap + training plan. *The cross-service demo story.*

### 3.5 `smarthr360-workload` — Mental workload service (Module 1)
- **Role**: mental workload calculator — scoring over work volume, task complexity, deadlines, interruptions/meetings, stress signals → burnout-risk alerts → task-rebalancing recommendations.
- **Source**: `calcul_charge` models (~200 lines: Tache, TacheCalibree, TacheImprevue, Alerte…). State: 🏗️ (scoring engine + alerts + APIs to build; algorithm described in rapport §3.2/§4.1)
- **Owns**: tasks, calibrated estimates, unexpected tasks, workload scores, alerts.

### 3.6 `smarthr360-policy-gen` — AI HR policy generator (Module 4)
- **Role**: strategic module — analyzes internal social data (turnover, wellbeing, performance), lets HR simulate policy impact (raise / mobility / telework, with intensity), and uses **Groq LLM** to generate prioritized policy recommendations with a decision dashboard.
- **Source**: 🛟 **rescue from `Module-4-update` branch** of the shared repo — a complete standalone Django project (`core/`: models 230 L, services 266 L, groq_service, dashboards, demo-data commands) never merged to main.
- **Rework**: convert template views → DRF APIs; token identity; remove committed `venv/` and `.env`.

### 3.7 `smarthr360-retention` — Retention chatbot service (Module 5)
- **Role**: detects disengagement signals (absenteeism, performance drop, contract end) → proactive chatbot conversation with the employee → simulates retention scenarios (raise, mobility, training) → proposes actions for HR validation.
- **Source**: 🛟 **rescue from `module-5` branch** — `negociateur_retention` app: `services/chatbot.py` (128 L), `detection.py`, `actions.py`, chat UI, models, views (~400 L total).
- **Rework**: DRF-ify, token identity; consider LLM upgrade in v2.

### 3.8 `smarthr360-frontend` — Web UI (deferred, D9)
- **Role**: role-aware UI consuming all service APIs. Existing HTMX/Tailwind app in the shared repo supersedes the old standalone frontend repo.
- **Start**: after v1.5 backend milestones. Tech decision (HTMX polish vs React rebuild) taken then.

### 3.9 `smarthr360` — Umbrella / platform repo
- **Contains**: pinned submodules of all services · `docker-compose.yml` (local dev) · k3s manifests or Helm chart (prod) · shared `jwt_auth` client package · ADRs (`docs/adr/`) · architecture diagram · demo seed scripts · env templates · platform README.

### 3.10 Deleted
- `prediction_competences` — zero code (only `.pyc` leftovers), concept covered by future-skills. Do not migrate.

---

## 4. Cross-cutting Conventions

1. **`jwt_auth` shared client** (lives in umbrella, installed/copied into each service): verifies RS256 tokens against auth's public key; exposes claim-based helpers (`has_hr_access`, `is_manager`, …) replacing all `from accounts.access import …` imports.
2. **Identity propagation**: services receive `Authorization: Bearer <JWT>`; user context = `user_id`, `role`, `email` claims. Never query auth's DB.
3. **Per-service PostgreSQL database** (one Postgres instance, separate DBs/schemas is fine for v1).
4. **Every repo's definition of done**: README (English, badges, purpose, quickstart, API table) · Dockerfile · `.env.example` · healthcheck endpoint (`/healthz`) · OpenAPI schema (drf-spectacular) · tests + coverage target 80% (cahier des charges NFR) · CI green.
5. **Standard CI (GitHub Actions)** per repo: ruff → mypy → tests+coverage → Docker build → push to GHCR on tag.
6. **Versioning**: semver tags per service; umbrella pins submodule commits and is itself tagged (`platform-v1.0.0`).

---

## 5. Security Remediation (do before/at repo creation)

| Item | Where found | Action |
|------|-------------|--------|
| Hardcoded DB password `majda2001` | shared repo `smarthr360/settings.py` | Never migrate; env var; change the local Postgres password |
| Insecure `SECRET_KEY` committed | shared repo settings | Regenerate per service, env var only |
| `production-secrets.txt` | `smarthr360_m3_future_skills` | Delete from repo; **rotate every secret inside**; fresh history (D6) removes it from the new remote |
| Committed `.env` (likely Groq API key) | `Module-4-update` branch | **Rotate the Groq key**; never commit `.env` |
| Committed `db.sqlite3`, `venv/`, `node_modules/`, `mlruns/`, logs | multiple repos/branches | Global `.gitignore` template in every new repo |

---

## 6. Roadmap

### v1 — Platform live (4 core services on k3s)

**Goal**: clean multi-repo architecture, deployed, documented. Headline: *"HR platform as microservices on Kubernetes, RS256 JWT, full CI."*

| Step | Work | Notes |
|------|------|-------|
| 1.1 | Reconcile m3: copy shared-repo `prediction_skills` back into `smarthr360_m3_future_skills` (one commit, junk excluded); clean repo (secrets, mlruns, node_modules) | Quick; verified one-directional |
| 1.2 | Create umbrella repo `smarthr360`; write `jwt_auth` RS256 client + key generation script | Unblocks everything |
| 1.3 | Create `smarthr360-auth`: extract `accounts`, add RS256 signing + public-key endpoint, fresh history | |
| 1.4 | Create `smarthr360-core-hr`: extract `hr`+`reviews`+`wellbeing`; User FKs → `user_id`; claim-based permissions via `jwt_auth`; profile-creation hook on registration | The 2–4 day surgery |
| 1.5 | Create `smarthr360-career-sim`: extract `simulateur_parcours`; token identity; skills-gap endpoint | |
| 1.6 | Wire m3 to `jwt_auth` (verify tokens from new auth) | |
| 1.7 | CI in all 5 repos (standard pipeline, §4.5); GHCR images | |
| 1.8 | Umbrella: submodules pinned, compose for local dev, seed/demo scripts, ADRs 001–005, architecture diagram, platform README | ADRs: microservices, umbrella, auth split, RS256, k3s |
| 1.9 | k3s deploy: VPS (~4 GB), k3s install, manifests/Helm (Deployments, Services, Ingress+TLS, Secrets, Postgres), public demo URL | |
| 1.10 | Verification: end-to-end smoke test (register → login → profile → prediction → skills-gap), coverage report, secret scan (gitleaks) on all repos | |

**Out of v1**: frontend, modules 1/4/5, old shared repo (ignored), old standalone frontend repo (archive).

### v1.5 — Complete the functional spec (modules 1, 4, 5 as new services)

**Goal**: 100% of the cahier des charges implemented. Each addition = its own release + LinkedIn post (*"added a new microservice to a running k8s platform"*).

| Step | Work |
|------|------|
| 1.5.1 | `smarthr360-retention`: rescue `module-5` branch code → new repo, DRF APIs, token identity, detection thresholds configurable, CI + deploy |
| 1.5.2 | `smarthr360-policy-gen`: rescue `Module-4-update` branch → new repo, strip venv/.env, DRF-ify simulation + Groq recommendations, dashboard API, CI + deploy |
| 1.5.3 | `smarthr360-workload`: build scoring engine on existing models (volume, complexity, deadlines, interruptions, stress signals), burnout alerts, rebalancing recommendations API, CI + deploy |
| 1.5.4 | Cross-service data feeds: retention detection reads core-hr (absence/performance) & workload (overload); policy-gen reads turnover/wellbeing aggregates |
| 1.5.5 | Platform release `platform-v1.5.0`; update architecture diagram + ADR for event/data-sharing pattern chosen |

### v2 — To be discussed (candidate items, not decided)

- **Frontend** (unblocks here at the latest): HTMX polish vs React SPA; role-based dashboards; the skills-gap flow as the hero UX.
- **Event-driven communication**: replace some HTTP calls with a broker (Redis streams / RabbitMQ / Kafka) — e.g., `user.registered` event creates profiles; detection signals feed retention.
- **API gateway** (Kong/Traefik) + rate limiting; central OpenAPI portal.
- **Observability stack platform-wide**: Prometheus + Grafana + Loki; extend m3's dashboards to all services; SLOs.
- **GDPR & security NFRs**: anonymization for wellbeing/retention data, audit logs ("traçabilité des décisions IA"), AES-256 at rest, gitleaks in CI.
- **Multilingual (i18n)** and **WCAG 2.1** accessibility (both are cahier des charges NFRs) — m3 taxonomy already has i18n fields.
- **Retention chatbot LLM upgrade** (Groq/other) with conversation memory.
- **Autoscaling & resilience**: HPA, PodDisruptionBudgets, backup/restore, 99.5% availability target.
- **SSO/OIDC** option on auth; refresh-token rotation & device management.

---

## 7. Portfolio Checklist (parallel to all versions)

- [ ] Umbrella README = 60-second system understanding: diagram, service table, quickstart, live demo link
- [ ] CI + coverage badges on every repo
- [ ] ADRs in `docs/adr/` (senior-signal artifact; interview answer bank)
- [ ] Live demo with 3 one-click role logins (Employee / Manager / HR) + seeded realistic data
- [ ] Screenshots/GIFs in READMEs
- [ ] LinkedIn cadence: one post per milestone (v1 architecture, k3s deploy, each v1.5 service, v2 features)
- [ ] CV lines ready: *"Designed and operated an 8-microservice HR platform (Django/DRF, PostgreSQL, Celery, MLflow) on self-managed Kubernetes (k3s) with full CI/CD to GHCR and RS256 JWT service-to-service auth."*

---

## 8. Reference Material

- `Cahier des charges fonctionnel SmartHR360.pdf` — official functional spec (5 modules + NFRs). NFRs *require* microservices, Docker, REST, CI, 80% coverage, GDPR, WCAG, multilingual.
- `rapport_SmartRH360.pdf` — academic report; module designs (use-case/sequence/class diagrams) and realized screenshots. **Where code is more advanced than the report (m3), code wins.**
- `SmartHR360/` folder (legacy shared repo) — reference only. Valuable branches: `Module-4-update` (policy generator), `module-5` (retention chatbot), `simulation_carriere`.
- Existing repos: `smarthr360_m3_future_skills` (kept), `smarthr360_backend` + `smarthr360-frontend` (sources to extract from, then archive).

## 9. Open Questions (for future sessions)

1. v2 scope selection & ordering (user: "we will discuss more things later").
2. Frontend technology decision (deferred by D9).
3. Postgres topology on k3s: single instance + multiple DBs vs per-service instances.
4. Event bus choice if/when adopted (v2).
5. VPS provider & sizing for k3s.
