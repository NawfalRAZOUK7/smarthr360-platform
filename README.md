# SmartHR360 — Platform

**Predictive HR platform built as microservices.** This umbrella repo
contains no application code: it pins the service repos at known-good
versions (git submodules), composes them for local development, and
will carry the k3s manifests for deployment.

## Architecture

```
                        ┌──────────────┐
                        │   frontend   │  (planned)
                        └──────┬───────┘
              HTTP/REST        │
     ┌──────────────┬──────────┼──────────────┬──────────────┐
     ▼              ▼          ▼              ▼              ▼
┌─────────┐   ┌──────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐
│  auth   │   │ core-hr  │ │future-skills│ │ career-sim │ │ v1.5: work- │
│ :8000   │   │  :8001   │ │   :8004    │ │   :8003    │ │ load/policy/│
└─────────┘   └──────────┘ └────────────┘ └────────────┘ │ retention   │
     ▲              │           │              │          └─────────────┘
     │   RS256 public-key verification (no calls to auth)
     └──────────────┴───────────┴──────────────┘
```

| Service | Repo | Role |
|---|---|---|
| auth | `smarthr360-auth` | Identity: users, roles, RS256 JWT issuing |
| core-hr | `smarthr360-core-hr` | Profiles, departments, skills, reviews, goals, wellbeing |
| future-skills | `smarthr360_m3_future_skills` | ML skill-demand prediction, MLflow, drift monitoring (Module 3) |
| career-sim | `smarthr360-career-sim` | Career trajectories, ML gap analysis, training recommendations (Module 2) |
| workload | `smarthr360-workload` | Mental workload scoring, burnout alerts (Module 1) |
| policy-gen | `smarthr360-policy-gen` | AI HR policy simulation & recommendations, Groq LLM (Module 4) |
| retention | `smarthr360-retention` | Retention chatbot: detection → conversation → HR actions (Module 5) |

Every service: own database, own Dockerfile, `/healthz/`, OpenAPI docs,
JWT verification via [`packages/smarthr360-jwt-auth`](packages/smarthr360-jwt-auth).

Decisions are documented as ADRs in [`docs/adr/`](docs/adr).

## Umbrella setup (once repos are on GitHub)

```bash
git clone --recursive git@github.com:NawfalRAZOUK7/smarthr360.git
cd smarthr360

# add services as submodules (first time):
git submodule add git@github.com:NawfalRAZOUK7/smarthr360-auth.git       services/smarthr360-auth
git submodule add git@github.com:NawfalRAZOUK7/smarthr360-core-hr.git    services/smarthr360-core-hr
git submodule add git@github.com:NawfalRAZOUK7/smarthr360-career-sim.git services/smarthr360-career-sim
git submodule add git@github.com:NawfalRAZOUK7/smarthr360_m3_future_skills.git services/smarthr360_m3_future_skills
git submodule add git@github.com:NawfalRAZOUK7/smarthr360-workload.git   services/smarthr360-workload
git submodule add git@github.com:NawfalRAZOUK7/smarthr360-policy-gen.git services/smarthr360-policy-gen
git submodule add git@github.com:NawfalRAZOUK7/smarthr360-retention.git  services/smarthr360-retention

# bump a service to its latest main:
git -C services/smarthr360-auth pull origin main
git add services/smarthr360-auth && git commit -m "bump auth to <version>"
```

## Run locally

```bash
./scripts/generate_rsa_keys.sh     # once: RS256 keypair in ./keys
cp .env.example .env               # set passwords/secret keys
docker compose up --build
```

| URL | Service |
|---|---|
| http://localhost:8000/docs/ | auth |
| http://localhost:8001/docs/ | core-hr |
| http://localhost:8003/healthz/ | career-sim |
| http://localhost:8004/ | future-skills |
| http://localhost:8005/docs/ | workload |
| http://localhost:8006/docs/ | policy-gen |
| http://localhost:8007/docs/ | retention |

## Shared package

`packages/smarthr360-jwt-auth` — RS256 verification client + claim-based
role helpers used by every service. `pip install -e` it for local work;
services reference it by git URL in their requirements.

## Roadmap

See [`docs/SMARTHR360_PLAN.md`](docs/SMARTHR360_PLAN.md): v1 (4 services
on k3s) → v1.5 (Modules 1, 4, 5 as new services) → v2 (frontend,
events, observability, GDPR hardening).
