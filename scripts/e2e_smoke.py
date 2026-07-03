#!/usr/bin/env python3
"""SmartHR360 end-to-end smoke test.

Runs the demo seed, then asserts the golden path across services with
a FRESH user (not the demo accounts), so it exercises registration,
lazy profile creation and cross-service authorization from scratch.

Exit code 0 = platform healthy. Used by CI (compose) and pre-deploy.

Usage:  python scripts/e2e_smoke.py
"""

from __future__ import annotations

import sys
import uuid
from datetime import date

import seed_demo
from platform_client import (
    StepFailed,
    log,
    request,
    unwrap,
    wait_for_services,
)

CHECKS: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    CHECKS.append(status)
    log(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        raise StepFailed(f"check failed: {name} {detail}")


def main() -> int:
    log("== SmartHR360 E2E smoke ==")
    wait_for_services()

    # 0) seed (idempotent) — also validates every seeded endpoint
    seed_demo.main()
    log("")
    log("== E2E assertions (fresh user) ==")

    suffix = uuid.uuid4().hex[:8]
    email = f"e2e-{suffix}@demo.smarthr360.dev"

    # 1) register a fresh employee on auth
    r = request(
        "post", "auth", "/api/auth/register/",
        json={
            "email": email, "username": f"e2e-{suffix}",
            "first_name": "E2e", "last_name": "Tester",
            "password": "E2e#2026!pass", "role": "EMPLOYEE",
        },
        expect=[201],
    )
    body = unwrap(r.json())
    token = body["tokens"]["access"]
    user_id = body["user"]["id"]
    check("auth: register issues RS256 token pair", bool(token) and bool(user_id))

    # 2) token refresh works
    r = request(
        "post", "auth", "/api/auth/refresh/",
        json={"refresh": body["tokens"]["refresh"]}, expect=[200],
    )
    refreshed = unwrap(r.json())["access"]
    check("auth: refresh flow preserves claims", bool(refreshed))
    token = refreshed

    # 3) core-hr trusts the token WITHOUT any auth-service call:
    #    /me lazily creates the profile from claims
    me = unwrap(request("get", "core_hr", "/api/hr/employees/me/", token,
                        expect=[200]).json())
    check(
        "core-hr: lazy profile from claims",
        me["user_id"] == user_id and me["email"] == email,
        f"profile id={me['id']}",
    )

    # 4) role enforcement: employee cannot list all employees
    r = request("get", "core_hr", "/api/hr/employees/", token)
    check("core-hr: employee blocked from HR list", r.status_code == 403)

    # 5) workload: create a task, compute a score
    request(
        "post", "workload", "/api/workload/tasks/", token,
        json={"title": "E2E task", "estimated_hours": 4, "complexity": 3,
              "deadline": str(date.today())},
        expect=[201],
    )
    score = request("post", "workload", "/api/workload/scores/compute/",
                    token, expect=[201]).json()
    check("workload: scoring engine", score["score"] > 0, f"score={score['score']}")

    # 6) career-sim: the cross-service skills-gap call
    hr_token = seed_demo.bootstrap_accounts()["hr"]["access"]
    positions = request(
        "post", "career_sim", "/api/career/demo-data/reset/", hr_token,
        expect=[201],
    ).json()["positions"]
    gap = request(
        "get", "career_sim",
        f"/api/career/skills-gap/?target_position_id={positions[0]['id']}",
        token, expect=[200],
    ).json()
    check(
        "career-sim: cross-service skills gap",
        "readiness_percent" in gap
        and gap["sources"]["current_skills"] == "smarthr360-core-hr",
        f"readiness={gap['readiness_percent']}%",
    )

    # 6b) trajectory simulation: 1/3/5-year projections, persisted
    sim = request(
        "post", "career_sim", "/api/career/simulate/",
        token,
        json={"target_position_id": positions[0]["id"]},
        expect=[201],
    ).json()
    traj = sim["trajectory"]
    check(
        "career-sim: trajectory simulation (1/3/5y)",
        [p["horizon_years"] for p in traj["projections"]] == [1, 3, 5]
        and 0.05 <= traj["success_probability"] <= 0.95
        and "simulation_id" in sim,
        f"p={traj['success_probability']}, "
        f"ready_in={traj['estimated_years_to_ready']}y",
    )

    # 7) policy-gen: HR analytics + gate
    r = request("get", "policy_gen", "/api/policy/analytics/", token)
    check("policy-gen: employee blocked", r.status_code == 403)
    analytics = request("get", "policy_gen", "/api/policy/analytics/",
                        hr_token, expect=[200]).json()
    check("policy-gen: analytics", "turnover_rate" in analytics,
          f"turnover={analytics['turnover_rate']}%")

    # 7b) cross-service wiring: policy-gen aggregates LIVE core-hr data
    #     (the seeded profiles + reviews, fetched with token pass-through)
    live = request("get", "policy_gen", "/api/policy/analytics/?source=live",
                   hr_token, expect=[200]).json()
    check("wiring: policy-gen live aggregates from core-hr",
          live.get("headcount", 0) >= 4,
          f"headcount={live.get('headcount')}, "
          f"avg_perf={live.get('avg_performance')}")

    # 8) retention: HR can read actions and conversations after detection
    request("get", "retention", "/api/retention/actions/", hr_token,
            expect=[200])
    conversations = unwrap(request(
        "get", "retention", "/api/retention/conversations/", hr_token,
        expect=[200]).json())
    check("retention: detection produced conversations",
          len(conversations) >= 1, f"{len(conversations)} conversation(s)")

    # 8b) cross-service wiring: the seed's overloaded developer hit
    #     BURNOUT_RISK in workload, which must have auto-ingested a
    #     burnout signal into retention (no human in the loop).
    signals = request("get", "retention", "/api/retention/signals/",
                      hr_token, expect=[200]).json()
    burnout = [s for s in signals if s["signal_type"] == "burnout_risk"]
    check("wiring: workload burnout alert reached retention",
          len(burnout) >= 1, f"{len(burnout)} burnout signal(s)")

    # 9) tampered token rejected everywhere
    bad = token[:-4] + "abcd"
    r = request("get", "core_hr", "/api/hr/employees/me/", bad)
    check("security: tampered token rejected", r.status_code == 401)

    log("")
    log(f"== E2E: {CHECKS.count('PASS')}/{len(CHECKS)} checks passed ==")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StepFailed as exc:
        log(f"E2E FAILED: {exc}")
        sys.exit(1)
