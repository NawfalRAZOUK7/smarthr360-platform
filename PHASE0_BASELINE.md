# SmartHR360 Phase 0 Baseline

Captured on 2026-07-19 in `/Users/nawfalrazouk/Smarthr360`. This file records observed state; it does not imply that a finding has been fixed.

## Git safety snapshot

No reset, checkout, clean, stash, or deletion was performed. Existing changes remain owned by the user.

| Repository | Branch | HEAD | Changed paths |
|---|---|---|---:|
| `smarthr360-platform` | `main` | `2fb7f28886d0a5e45a3eeddbf7b8c7f54a557ba4` | 28 |
| `smarthr360-auth` | `main` | `7e75bafe63b98cea441facd56af4a779a6639d15` | 2 |
| `smarthr360-core-hr` | `main` | `6553ea25c1da0f73367e3cda0e477473d613415b` | 0 |
| `smarthr360-career-sim` | `main` | `73f07c0ca5ce902ac74ac7d76d619272b16b4deb` | 1 |
| `smarthr360-workload` | `main` | `ea917d6802c8cd169ffec2efc2be065137f43a7f` | 0 |
| `smarthr360-policy-gen` | `feat/smarthr360-integration` | `0afaf7f719295e3a51cfee1b5c25b0f03ac85b4e` | 0 |
| `smarthr360-retention` | `main` | `37a7be5452dd779d69f9524622b3c8599285fc40` | 0 |
| `smarthr360_m3_future_skills` | `develop` | `94d81f015195a67e801cc523690c338a541db185` | 2 |

The frontend directory exists at `../smarthr360-frontend` but has no independent `.git` metadata in this workspace. Its files must therefore be protected as unversioned workspace content.

## Initial architecture inventory

- Compose services: PostgreSQL; seven Django services (`auth`, `core-hr`, `career-sim`, `workload`, `policy-gen`, `retention`, `future-skills`); Next.js frontend; Prometheus; Grafana; Alertmanager.
- Django app/migration file counts: auth 1/10, Core HR 4/13, Career Sim 1/3, Workload 1/2, Policy Gen 1/1, Retention 1/5, Future Skills 3/22.
- Shared wheels: `smarthr360-jwt-auth` and `smarthr360-integration`.
- Background execution code is currently concentrated in Future Skills: Celery configuration/tasks/monitoring plus thread-based prediction execution.
- Tracked ML/data files are currently confined to Future Skills: one pickle model, a primary CSV dataset, fixtures/templates, and test datasets.
- Compose health checks exist for PostgreSQL and the Django services; the frontend and observability services do not all expose Compose health checks.
- Service ordering primarily depends on PostgreSQL health, with selected `service_started` dependencies on auth/Core HR.

### Django ownership map

| Service | Owned Django apps | Migration files | Test files |
|---|---|---:|---:|
| Auth | `accounts` | 10 | 8 |
| Core HR | `hr`, `integration`, `reviews`, `wellbeing` | 13 | 7 |
| Career Sim | `simulateur_parcours` | 3 | 5 |
| Workload | `workload` | 2 | 4 |
| Policy Gen | `policies` | 1 | 4 |
| Retention | `retention` | 5 | 4 |
| Future Skills | `accounts`, `celery_monitoring`, `future_skills` | 22 | 29 |
| Frontend | Next.js application; no Django apps | n/a | 3 Playwright spec files |

### Database and dependency boundaries

- PostgreSQL is one container with separate databases initialized for each service. No cross-service Django foreign keys were found in the architectural pattern; identity is passed as JWT claims and stored IDs.
- Every non-Future-Skills backend currently has one `requirements.txt`; Future Skills splits base, development, ML, logging, security, and Celery requirements and also carries Python-version lock/hash files.
- The frontend uses `package.json` plus `package-lock.json`.
- All satellite services consume locally copied wheel builds of the two shared packages. Package version/release synchronization is architectural debt for later phases.
- Future Skills contains both Celery result-table integration and thread-based prediction execution, but the Compose baseline has no Redis broker or Celery worker. This is an incomplete optional capability rather than a platform-wide queue contract.
- Future Skills owns the only committed sklearn artifact and training dataset. Career Sim logs that its optional gap-analysis model is absent.

### Health and Compose dependency inventory

- PostgreSQL has a real `pg_isready` health check. The seven Django application containers report healthy through image/Compose checks.
- Manual `/health/` returned 404 for Auth, Core HR, Career Sim, Workload, Policy Gen, and Retention; Future Skills `/api/health/` and frontend `/login` returned 200. The mismatch is a configuration/contract defect even though Docker health currently passes.
- Frontend, Prometheus, Grafana, and Alertmanager have no consistent Compose health contract.
- Observability uses mutable `latest` image tags, another reproducibility/configuration debt item.

## Baseline build and runtime findings

- All eight application images built successfully with `docker compose up -d --build`.
- Compose startup failed during container recreation because stale/dead replacement containers produced a Docker name conflict for Career Sim.
- The failed recreation left Compose pointing at created containers while older same-name application containers continued running. Management-command baselines cannot be trusted until this container-state defect is normalized.
- Alertmanager was already exited with status 1 and requires separate log/config diagnosis.
- Backend builds emitted `useradd` warnings because UID 10001 is above Debian's configured system UID maximum.
- Auth static collection emitted an expected development-only ephemeral-RSA-key notice during its image build.
- The frontend transferred about 255 MB of build context, spent about 260 seconds on `COPY . .`, about 156 seconds compiling, and about 210 seconds in TypeScript checking. This is a build-context/resource performance problem.
- Future Skills used its explicit build settings successfully and collected static files without the former production-setting warnings.

## Migration and system-check baseline

All seven services passed `makemigrations --check --dry-run` and `manage.py check`. `migrate --noinput` was clean and idempotent for six services; Future Skills applied the newly added `accounts.0004_alter_user_options` migration successfully.

## Test baseline

| Suite | Result |
|---|---|
| Auth | 58 passed |
| Core HR | 41 passed |
| Career Sim | 22 passed |
| Workload | 31 passed |
| Policy Gen | 27 passed |
| Retention | 26 passed |
| Future Skills | 181 passed, 10 failed, 2 skipped (193 total) |
| Frontend production build | passed |
| Playwright E2E | 30 passed, 5 failed (35 total; retries also failed) |

Future Skills failure groups:

- Six API architecture/versioning/CORS/rate-limit workflow assertions expect anonymous 200 responses although the current security contract returns 403.
- One cache test expects `X-Cache-Hit: true` on the second request but receives `false`.
- The training-small test expects 201 but the configured artifact dataset is absent and the endpoint returns 400.
- Test-path Celery monitoring attempts to persist a `TaskResult` without `task_id`, violating its non-null database constraint.
- Test JWT fixtures use a 13-byte HMAC key and emit `InsecureKeyLengthWarning`.

Playwright deterministic failures:

- HR admin-block test races a disabled login form in the shared login helper.
- Policy simulation does not render the expected Turnover result, preventing both the simulation and apply/outcome flows.
- Policy Outcomes does not render its expected dashboard heading.
- Skill Gaps does not render the expected Training plan section.

The Future Skills bulk import with auto-prediction, Monitoring/drift surface, dataset upload/training control, guest read-only login, workload write flow, retention flow, and the other cross-service journeys passed.

## Secret and personal-data safety audit

- A tracked sensitive-filename scan across all Git repositories found only `.env.example` templates.
- Runtime `.env` files and private-key filename patterns are ignored. The platform explicitly ignores `keys/jwt_private.pem`.
- Public-key exceptions are intentional because satellite services need public verification material; private signing keys must remain auth-owned and untracked.
- The committed Future Skills CSV/pickle artifacts still require content/provenance classification before the Phase 0 safety item can close.

The dataset contains role/skill feature rows and no employee identity columns. Its SHA-256 is `3dcd47dce736a7745bf396eb85eba2ad03b4d7941b69964a2fb7f1f49ad631e2`. The pickle is an sklearn Pipeline/RandomForest artifact with SHA-256 `7bf2963a9b88d82075ef33569c49c5f288d13cc4c414b6bb870b75b406dc1eb`; pickle provenance/integrity remains an ML-lifecycle risk, but it is not personal data.

Gitleaks scanned the complete platform worktree. Its actionable filesystem hits were runtime `.env` and `keys/jwt_private.pem`; both are ignored and untracked. Remaining hits are examples/schema/code identifiers or archived documentation and require suppression hygiene, not secret rotation. The only tracked sensitive filename is `.env.example`. Compose retains the documented local-only Grafana default `admin`, which is a production-validation defect, not a confidential committed credential.

## Finding classification

| Class | Baseline findings |
|---|---|
| Product defects | Policy simulation/outcome UI paths and Skill Gaps training-plan rendering do not satisfy their E2E contracts. |
| Obsolete tests | Future Skills anonymous-access/versioning/rate-limit expectations conflict with the authenticated API security contract. |
| Configuration defects | Inconsistent health URLs; missing health checks for frontend/observability; Alertmanager gossip needed explicit local handling; Grafana provisioning directories/plugin updater behavior; no Redis/worker despite Celery configuration; local Grafana default password; mutable observability tags. |
| Architectural debt | Future Skills local accounts app; per-service copied wheels/settings/Docker divergence; mixed thread/Celery execution; committed unversioned pickle/data lifecycle; generic result tables without a decided platform contract. |
| Security warnings | Short HMAC test key; local default Grafana credential; pickle deserialization/provenance risk. Runtime private JWT material is ignored and untracked. |
| Expected optional-capability notices | Missing `GROQ_API_KEY`, mocked cross-service outages, and missing Career Sim optional ML model. These should become structured/silenced in tests, not treated as production success signals. |
| Performance/resource problems | Large frontend build context; backend `useradd` warnings; Gunicorn worker timeout/SIGKILL storms under the full run; slow Future Skills metrics/API calls; Prometheus multiprocess label-clearing warning; login-helper race under load. |
| Environment/runtime-state defects | Docker stale replacement-container collision before clean recreation; Grafana bundled-plugin `permission denied`; missing provisioning directories. |

## Rollback and compatibility policy

Every later phase must use the following gate, refined by its phase-specific checklist:

1. Prefer additive database migrations. Do not drop/rename a field or table until all readers and writers have used the replacement for at least one release window and a production-like backup/restore rehearsal succeeds.
2. Keep old API claims, endpoints, artifact readers, queue payload versions, and configuration names available for at least one compatibility release when a rolling deployment can mix versions.
3. Before deployment, record database backup identifiers, image digests, package versions, artifact checksums, and the last known-green test/health result.
4. Roll back when migrations fail, unauthorized access broadens, cross-service identity IDs diverge, error/latency thresholds regress materially, queues cannot drain safely, model acceptance/drift gates fail, or required E2E journeys fail.
5. Application rollback means redeploying the prior immutable image/config while leaving additive schema in place. Destructive reverse migrations require an explicit restore plan and approval.
6. Background-job changes must support draining old workers, versioned payloads, idempotent redelivery, and disabling new producers before worker rollback.
7. ML changes must retain the prior model, dataset manifest, checksum, feature schema, and promotion pointer so rollback is an atomic pointer/config change rather than retraining.
8. Identity/accounts migration must preserve the Future Skills local account tables in read-only compatibility mode until canonical-ID reconciliation, token contract tests, and rollback rehearsal pass.
9. Shared-package changes require a compatibility matrix across all consuming services; a breaking major version cannot remove the previous supported line in the same deployment wave.
10. A phase is complete only after its rollback evidence, compatibility-window owner, and removal date are documented.
