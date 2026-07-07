# smarthr360-integration

Shared enterprise-integration toolkit for SmartHR360 microservices. Written once,
vendored/installed into every service so cross-cutting concerns are **never
copy-pasted** — the platform's anti-duplication rule.

## What's inside

| Module | Purpose |
|---|---|
| `observability` | Idempotent Prometheus metric factories (`get_counter`, `get_gauge`, `get_histogram`) — safe to call at import time / on reload |
| `api` | Standardized error envelope (`bad_request`, `not_found`, …) and `StandardEnvelopePagination` |
| `history` | Reusable Slowly Changing Dimension (Type 2): abstract `SCD2HistoryBase` + idempotent `snapshot_history` + signal suppression |
| `clients` | Inter-service HTTP clients (`CoreHRClient`) — read data you don't own instead of duplicating it |
| `analytics` | Shared trend maths (`linear_trend`, `project`, `clamp`) with optional scikit-learn path |

## The three anti-duplication rules

1. **One datum, one owner.** core-hr owns employees & skills; retention owns
   signals; etc. Never re-model another service's data.
2. **Cross-cutting = shared lib.** Metrics, pagination, errors, SCD2, clients
   live here and are imported, not copied.
3. **Everything else flows service-to-service** via `clients` (callers pass
   their JWT through).

## Usage sketch

```python
from smarthr360_integration.observability import get_counter
from smarthr360_integration.api import StandardEnvelopePagination, not_found
from smarthr360_integration.history import SCD2HistoryBase, snapshot_history
from smarthr360_integration.clients import CoreHRClient

# read competencies owned by core-hr (no local Skill table)
client = CoreHRClient("http://core-hr:8000", token=request.auth_token)
comps = client.person_competencies(department="ENG")
```

## Build & vendor

```bash
cd packages/smarthr360-integration
python -m build            # produces dist/smarthr360_integration-0.1.0-py3-none-any.whl
# then vendor the wheel into each service (as done for smarthr360-jwt-auth)
```
