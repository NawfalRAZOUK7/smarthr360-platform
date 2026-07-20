# SmartHR360 Professionalization Roadmap

This is the implementation source of truth. Check an item only after its code, migration path, documentation, and proportional verification have completed. Existing words from the approved architecture proposal are preserved verbatim in the final section.

## Master checklist

### Phase 0 — Safety, inventory, and baselines

- [x] Record the current Git state of the platform, every service repository, and the frontend without overwriting unrelated work. Evidence: `PHASE0_BASELINE.md`.
- [x] Inventory every Django app, migration, database dependency, shared wheel, background task, artifact path, health check, warning, test suite, and Compose dependency. Evidence: `PHASE0_BASELINE.md`.
- [x] Capture baseline results for image builds, migration checks, Django system checks, backend tests, frontend build, E2E, container health, and runtime warnings. Evidence: `PHASE0_BASELINE.md`.
- [x] Classify findings as product defects, obsolete tests, configuration defects, architectural debt, security warnings, expected optional-capability notices, or performance/resource problems. Evidence: `PHASE0_BASELINE.md`.
- [x] Preserve secrets outside source control and verify that no generated key, password, token, dataset containing personal data, or environment file is committed. Evidence: tracked-file audit and redacted Gitleaks classification in `PHASE0_BASELINE.md`.
- [x] Define rollback criteria and compatibility windows for every migration phase. Evidence: `PHASE0_BASELINE.md`.

### Phase 1 — Current correctness and warning-free foundations

- [x] Fix all unapplied or missing Django migrations. Future Skills `accounts.0004_alter_user_options` is present and applied.
- [x] Make `makemigrations --check --dry-run` pass for every service. Verified for all seven services on 2026-07-19.
- [x] Make `migrate --noinput` pass cleanly and idempotently for every service. A second full pass reported no migrations to apply on 2026-07-19.
- [ ] Make `manage.py check` and deployment-oriented checks pass under the appropriate environment profile.
- [x] Remove hidden build failures such as `collectstatic ... || true`. All backend Dockerfiles now fail explicitly when static collection fails; full image build passed.
- [ ] Supply explicit build-safe settings for image-build Django commands.
- [ ] Separate development, test, build, and production validation so production warnings do not appear during tests or builds.
- [x] Fix all current backend test failures without weakening authorization, team scoping, or assertions. Future Skills now runs under its isolated test profile, removes the test-only permission bypass, and passes all 193 tests (2 skipped); the other six services' 205 tests remain green.
- [ ] Fix all deterministic frontend E2E failures at their product cause.
- [ ] Stabilize resource-related E2E flakes and replace timing-only waits with observable application states.
- [ ] Make health checks accurate, lightweight, consistent, and independent of authenticated endpoints.
- [ ] Verify every container becomes healthy after a full rebuild.

### Phase 2 — Shared identity and accounts boundary

- [ ] Keep the canonical Django `accounts` app and credential ownership in the auth service only.
- [ ] Inventory every Future Skills dependency on its local `accounts` app, user model, migrations, admin, serializers, permissions, tests, and foreign keys.
- [ ] Freeze new functionality in the Future Skills local `accounts` app.
- [ ] Define a compatibility/data-migration map from local Future Skills users to canonical auth `user_id` values.
- [ ] Extract or finish the shared RS256 JWT authentication/authorization package.
- [ ] Standardize JWT issuer, audience, algorithm, key rotation, clock skew, token claims, roles, and groups across services.
- [ ] Standardize `EMPLOYEE`, `MANAGER`, `HR`, and `ADMIN` roles plus `AUDITOR` and `SUPPORT` group semantics.
- [ ] Store external auth identities by value in domain services and forbid cross-service database foreign keys.
- [ ] Replace Future Skills runtime authentication with the shared JWT package.
- [ ] Convert Future Skills domain references from local user foreign keys to canonical auth `user_id` values through additive migrations.
- [ ] Preserve local account tables and migrations during the rollback window.
- [ ] Add identity contract tests across auth and every consuming service.
- [ ] Remove the Future Skills local accounts app from active runtime only after data migration, compatibility verification, and rollback approval.

### Phase 3 — Shared settings and service contracts

- [ ] Create or extend a versioned shared Django platform-settings package.
- [ ] Share environment parsing and required-variable validation.
- [ ] Share database configuration helpers without sharing databases.
- [ ] Share CORS and trusted-origin defaults with service-specific overrides.
- [ ] Share JWT verification settings.
- [ ] Share security headers and secure-cookie defaults.
- [ ] Share logging, metrics, health-check, and test-setting helpers.
- [ ] Give every service explicit `base.py`, `development.py`, `test.py`, and `production.py` settings modules.
- [ ] Ensure production fails fast for unsafe or missing configuration.
- [ ] Ensure development and test do not emit misleading production warnings.
- [ ] Document the stable configuration contract and upgrade process.

### Phase 4 — Standard multi-stage container builds

- [ ] Define a standard backend Docker architecture: `base → dependencies → test → runtime`.
- [ ] Convert auth to the standard multi-stage build.
- [ ] Convert Core HR to the standard multi-stage build.
- [ ] Convert Career Sim to the standard multi-stage build.
- [ ] Convert Workload to the standard multi-stage build.
- [ ] Convert Policy Gen to the standard multi-stage build.
- [ ] Convert Retention to the standard multi-stage build.
- [ ] Align Future Skills with the same stages while retaining its ML dependency layer.
- [ ] Pin and hash production dependencies where supported.
- [ ] Keep compilers, headers, Git, and build tools out of runtime images.
- [ ] Run every service as a non-root user with explicit writable directories.
- [ ] Add consistent OCI metadata, health checks, stop signals, and entrypoints.
- [ ] Use BuildKit caches without making builds depend on mutable cache contents.
- [ ] Add explicit test image targets.
- [ ] Generate and retain software bills of materials and vulnerability scan results in CI.

### Phase 5 — Shared observability

- [ ] Move reusable observability into the shared integration package.
- [ ] Standardize JSON structured logging.
- [ ] Standardize correlation and request IDs across incoming and outgoing calls.
- [ ] Include service name, version, environment, trace context, and safe identity metadata.
- [ ] Standardize request duration and response-status metrics.
- [ ] Standardize exception records without leaking secrets or personal data.
- [ ] Standardize Prometheus metric names and bounded-cardinality labels.
- [ ] Add OpenTelemetry-compatible traces for HTTP, database, queue, and background jobs.
- [ ] Propagate trace/correlation context through service calls and Celery tasks.
- [ ] Keep domain-specific middleware inside its owning service.
- [ ] Add dashboards and actionable alerts for availability, latency, errors, queue depth, worker failures, and model drift.

### Phase 6 — Durable background execution

- [ ] Add one authenticated, persistent Redis broker to Compose with health checks and resource limits.
- [ ] Define a versioned shared Celery convention/package.
- [ ] Standardize serialization, accepted content types, UTC handling, acknowledgements, prefetch, retries, backoff, jitter, time limits, and dead-letter/failure handling.
- [ ] Keep ordinary CRUD synchronous.
- [ ] Keep domain run models such as `PredictionRun` and `TrainingRun` as the user-facing source of truth.
- [ ] Decide per service whether generic Celery result storage adds value; do not install it everywhere by default.
- [ ] Add a Future Skills worker for prediction recalculation and ML training.
- [ ] Replace Future Skills background threads with durable queued jobs after compatibility verification.
- [ ] Add a Workload worker/beat schedule for scoring and forecasting where required.
- [ ] Add a Retention worker/beat schedule for batch detection where required.
- [ ] Add a Core HR worker/beat schedule for notification digests where required.
- [ ] Add a Policy Gen worker for expensive document/report generation where required.
- [ ] Make tasks idempotent and safe under retry and duplicate delivery.
- [ ] Add task ownership, progress, cancellation, timeout, retry, and failure visibility.
- [ ] Add queue contract, worker restart, broker outage, and duplicate-delivery tests.

### Phase 7 — Professional ML artifact and dataset lifecycle

- [ ] Keep scikit-learn and ML-only dependencies out of non-ML services.
- [ ] Assign explicit model ownership to Future Skills, Retention, Workload, and Career Sim as applicable.
- [ ] Standardize the artifact layout for models, datasets, metadata, results, and caches.
- [ ] Define a versioned artifact manifest schema.
- [ ] Record model version and immutable artifact identifier.
- [ ] Record training timestamp and code revision.
- [ ] Record dataset version and checksum.
- [ ] Record feature and target schemas.
- [ ] Record dependency/library versions.
- [ ] Record evaluation metrics and acceptance thresholds.
- [ ] Record approval, promotion, rollback, and retirement status.
- [ ] Validate uploaded datasets before promotion and preserve provenance.
- [ ] Prevent containers from silently replacing production datasets or models.
- [ ] Add local filesystem storage for development and an object-storage abstraction for production.
- [ ] Support S3, MinIO, or Azure Blob through configuration rather than service rewrites.
- [ ] Add artifact integrity, compatibility, rollback, and missing-artifact tests.
- [ ] Connect model versions and dataset provenance to prediction runs and drift snapshots.

### Phase 8 — Test architecture

- [ ] Define shared test markers and directory conventions.
- [ ] Separate unit, model/command, API, permission/team-scope, integration, contract, migration, asynchronous-job, frontend-component, and E2E tests.
- [ ] Correct or retire obsolete Future Skills anonymous-access expectations.
- [ ] Make caching tests assert the supported cache contract.
- [ ] Make training tests use explicit temporary/versioned datasets.
- [ ] Remove test dependence on production warnings, unavailable external services, and mutable global state.
- [ ] Add migration-forward tests and selected rollback/compatibility tests.
- [ ] Retain seed idempotency tests for every service.
- [ ] Add authentication and authorization contract tests for every role/group.
- [ ] Add team-scoping and cross-tenant isolation tests.
- [ ] Add deterministic async job tests with eager/test worker modes.
- [ ] Add frontend component tests for permissions and loading/error states.
- [ ] Reduce the E2E suite to high-value deterministic cross-service journeys while retaining necessary regression coverage.
- [ ] Run destructive or expensive integration tests in isolated databases and artifact directories.

### Phase 9 — CI/CD quality gates

- [ ] Gate formatting, import ordering, linting, and type checking.
- [ ] Gate `makemigrations --check --dry-run` for every Django service.
- [ ] Gate migrations against clean and representative upgraded databases.
- [ ] Gate Django system and deployment checks under correct profiles.
- [ ] Gate shared-package compatibility and contract tests.
- [ ] Gate unit and service API suites.
- [ ] Gate container builds and container health.
- [ ] Gate dependency and image vulnerability scans.
- [ ] Gate secret scanning and generated-artifact checks.
- [ ] Gate frontend production build and deterministic E2E.
- [ ] Publish test reports, coverage, SBOMs, migration plans, and image digests.
- [ ] Add staged deployment, smoke tests, observability checks, and automated rollback criteria.

### Phase 10 — Production data and database isolation

- [ ] Document ownership of every table and migration.
- [ ] Keep one logical database/schema and credentials boundary per service in production.
- [ ] Remove accidental cross-service ORM/database dependencies.
- [ ] Use APIs/events for cross-service data exchange.
- [ ] Define transactional outbox/idempotent consumer patterns where event delivery is introduced.
- [ ] Encrypt traffic and credentials, rotate secrets, and apply least privilege.
- [ ] Define backup, restore, disaster-recovery, retention, and data-erasure procedures per service.
- [ ] Load-test critical APIs, workers, queues, and ML inference paths.
- [ ] Complete operational runbooks and ownership/escalation documentation.

## Completion gate

- [ ] Every checklist item above is completed or explicitly deferred with owner, reason, risk, and target date.
- [ ] Full ordered verification is green from a clean checkout and clean databases.
- [ ] Upgrade verification is green from the current deployed schema and representative data.
- [ ] No warning is hidden or suppressed without a documented rationale.
- [ ] No secret or sensitive dataset is committed.
- [ ] Architecture documentation matches the implemented system.

## Approved architecture proposal — preserved verbatim

Your instinct to standardize the platform is right, but sharing everything across every service would make the architecture less professional. The best design is to standardize infrastructure and contracts while keeping domain ownership isolated.

Recommended target architecture:

| Capability | Professional placement |
|---|---|
| User accounts and passwords | Auth service only |
| JWT validation, roles, groups, permissions | Shared Python package used by every backend |
| Employee identity references | `user_id` stored by value in domain services |
| Celery broker | One shared Redis service |
| Celery workers | Only for services that execute durable background jobs |
| Celery result tables | Only in services that own Celery jobs, or replace with domain run tables |
| ML libraries, datasets, models | Only ML-owning services |
| Logging, request IDs, metrics | Shared Python observability package |
| Production validation | Shared Django settings package with service-specific extensions |
| Docker architecture | Standard multi-stage template for every backend |
| Tests | Shared conventions and utilities, but service-specific suites |
| Database | One logical database/schema per service in production |

### Accounts

Do not merge the Django `accounts` app into every module.

The professional design is:

```text
auth service
└── accounts app
    ├── User
    ├── passwords
    ├── MFA
    ├── groups
    ├── login activity
    └── token issuance

shared JWT package
└── authentication and authorization code

domain services
└── user_id stored by value
```

Future Skills currently has a local `accounts` app because it evolved as a standalone application. It should be migrated gradually:

1. Freeze its local account functionality.
2. Replace authentication with the shared RS256 JWT package.
3. Convert domain references to auth `user_id` values.
4. Preserve the existing tables and migrations temporarily for rollback/data migration.
5. Remove the app from active runtime only after all references are migrated.

We should not physically delete its migrations or tables during the first phase.

### Celery and result tables

Celery runs background jobs outside web requests. For example:

```text
Browser → Django API → Redis queue → Celery worker → ML training
                                      ↓
                               PredictionRun status
```

This is useful for:

- ML training
- Large prediction recalculations
- Bulk imports
- Email digests
- Scheduled workload scoring
- Retention detection batches
- Document/report generation

`django_celery_results` stores generic task status and results in Django tables. However, SmartHR360 already has better domain models such as `PredictionRun` and `TrainingRun`.

My recommendation:

- Add one shared Redis broker to Compose.
- Use Celery only where background durability is required.
- Keep `PredictionRun`, `TrainingRun`, and similar domain run tables as the user-facing source of truth.
- Do not install `django_celery_results` in every service.
- Initially enable workers for:
  - Future Skills
  - Workload scheduled scoring
  - Retention detection
  - Core HR notification digests
  - Policy document generation
- Keep ordinary CRUD synchronous.
- Replace the Future Skills background thread with Celery after the shared queue is operational.

A thread can disappear when Gunicorn restarts; a queued Celery job survives the web worker.

### ML artifacts and datasets

Do not install scikit-learn in every service.

Recommended ownership:

- Future Skills owns future-skill prediction models and training datasets.
- Retention may own a separate attrition model.
- Workload may own workload forecasting.
- Career Sim may own readiness/gap models.

Standardize their artifact interface:

```text
/artifacts
├── models/
│   └── model-name/version/model.pkl
├── datasets/
│   └── dataset-name/version/data.csv
├── metadata/
│   └── manifest.json
└── results/
```

Each model should have a manifest containing:

- model version
- training timestamp
- dataset checksum
- feature schema
- library versions
- evaluation metrics
- approval status

For production, artifacts should ultimately live in S3/MinIO/Azure Blob rather than inside a container image.

### Docker

Every backend should use the same multi-stage structure:

```text
base → dependencies → test → runtime
```

Benefits:

- build dependencies stay outside runtime images
- non-root runtime user
- reproducible dependency installation
- smaller attack surface
- consistent health checks
- reusable BuildKit caches
- explicit test image target

Future Skills will remain larger because NumPy, pandas and scikit-learn are large, but its build behavior will become consistent with the others.

Django commands such as `collectstatic` should not be hidden behind `|| true`. Build-safe settings must be supplied, and genuine errors must fail the image build.

### Settings and validation

Create a shared settings package containing:

- environment parsing
- database configuration
- CORS defaults
- JWT verification
- logging
- metrics
- security headers
- health checks
- test defaults

Each service then has:

```text
settings/
├── base.py
├── development.py
├── test.py
└── production.py
```

Production validation should fail fast for actual unsafe configuration, while development and test modes should not print misleading production warnings.

### Logging and monitoring

Move reusable observability into the existing shared integration package:

- JSON structured logs
- correlation/request IDs
- service name and version
- request duration
- standardized error records
- Prometheus metrics
- OpenTelemetry-compatible traces

Do not share domain-specific middleware. Only the infrastructure layer should be shared.

### Testing

The goal should not be “190 tests in every service.” Test count reflects domain complexity.

Standardize test layers instead:

- unit tests
- model/command tests
- API permission and team-scope tests
- integration tests
- contract tests for JWT and shared packages
- migration tests
- seed idempotency tests
- asynchronous job tests
- frontend component tests
- a smaller deterministic E2E suite

Future Skills’ current suite mixes architecture experiments, old anonymous-access expectations, live configuration, and current product behavior. That is why it produces contradictory failures. Those tests need classification and correction rather than simply being suppressed.

### Recommended implementation order

1. Fix all current migrations, test failures and build warnings.
2. Extract shared JWT/settings/observability packages.
3. Migrate Future Skills away from its local accounts runtime.
4. Standardize backend multi-stage Dockerfiles.
5. Add Redis and a shared Celery convention.
6. Move Future Skills async jobs from threads to Celery.
7. Add workers selectively to other services.
8. Introduce versioned ML artifact manifests and object-storage support.
9. Split tests into unit, integration, contract and E2E stages.
10. Add CI gates for migrations, formatting, security, builds and contracts.

I recommend following this phased architecture instead of copying every Future Skills component into every service. It provides consistency without turning the microservices into duplicated monoliths.
