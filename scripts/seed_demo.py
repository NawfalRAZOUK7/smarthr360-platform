#!/usr/bin/env python3
"""SmartHR360 platform demo seed.

Seeds a coherent demo story across every running service, over HTTP,
exactly as a client would — proving the platform end to end:

  auth        4 demo accounts (admin / hr / manager / employee)
  core-hr     departments, profiles (with manager link), skill catalog,
              skill evaluations, review cycle + goal, wellbeing survey
  workload    tasks + workday signal for the employee, computed scores
              (one healthy, one overloaded -> burnout alert)
  career-sim  3 target positions + skills-gap for the employee
  policy-gen  analytical store reset
  retention   engagement store rows + risk detection -> conversation

Idempotent: safe to run repeatedly. Requires the services running
(docker compose up, or any URLs via SMARTHR_<NAME>_URL env vars).

Usage:  python scripts/seed_demo.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from platform_client import (
    DEMO_PASSWORD,
    StepFailed,
    bootstrap_accounts,
    log,
    request,
    unwrap,
    wait_for_services,
)

SKILLS = [
    ("Python", "PY"), ("Django", "DJ"), ("Kubernetes", "K8S"),
    ("SQL", "SQL"), ("Communication", "COMM"),
    ("Machine Learning", "ML"), ("Project Management", "PM"),
]

# employee's current levels (core-hr scale 1-4)
EMPLOYEE_SKILLS = {"PY": 4, "DJ": 2, "SQL": 2, "COMM": 2}


def seed_core_hr(acc) -> dict:
    hr = acc["hr"]["access"]
    log("[core-hr] departments, profiles, skills, review, survey")

    # departments (idempotent by code)
    departments = {}
    existing = unwrap(request("get", "core_hr", "/api/hr/departments/", hr).json())
    by_code = {d["code"]: d for d in existing}
    for name, code in [("Engineering", "ENG"), ("Human Resources", "HR"), ("Data", "DATA")]:
        if code in by_code:
            departments[code] = by_code[code]
        else:
            departments[code] = unwrap(request(
                "post", "core_hr", "/api/hr/departments/", hr,
                json={"name": name, "code": code}, expect=[201],
            ).json())

    # profiles (idempotent: employees/me/ lazily creates; we upgrade via HR list)
    profiles = {}
    existing = unwrap(request("get", "core_hr", "/api/hr/employees/", hr).json())
    by_user = {p["user_id"]: p for p in existing}
    plan = [
        ("hr", "HR", "HR Business Partner", None),
        ("manager", "ENG", "Engineering Manager", None),
        ("employee", "ENG", "Software Developer", "manager"),
        ("admin", "HR", "Platform Administrator", None),
    ]
    for key, dept, title, manager_key in plan:
        a = acc[key]
        payload = {
            "user_id": a["user_id"], "email": a["email"],
            "first_name": a["email"].split("@")[0].split("-")[-1].title(),
            "user_role": a["role"], "job_title": title,
            "department_id": departments[dept]["id"],
            "hire_date": str(date.today() - timedelta(days=700)),
        }
        if manager_key and manager_key in profiles:
            payload["manager_id"] = profiles[manager_key]["id"]
        if a["user_id"] in by_user:
            # profile already exists (auth provisioning creates it at
            # registration) — enrich it with org data instead
            existing = by_user[a["user_id"]]
            patch = {k: v for k, v in payload.items()
                     if k in ("department_id", "manager_id", "job_title",
                              "hire_date", "user_role")}
            profiles[key] = unwrap(request(
                "patch", "core_hr", f"/api/hr/employees/{existing['id']}/",
                hr, json=patch, expect=[200],
            ).json())
        else:
            profiles[key] = unwrap(request(
                "post", "core_hr", "/api/hr/employees/", hr,
                json=payload, expect=[201],
            ).json())
    log(f"  profiles: { {k: p['id'] for k, p in profiles.items()} }")

    # skill catalog (idempotent by code)
    skills = {}
    existing = unwrap(request("get", "core_hr", "/api/hr/skills/", hr).json())
    by_code = {s["code"]: s for s in existing}
    for name, code in SKILLS:
        skills[code] = by_code.get(code) or unwrap(request(
            "post", "core_hr", "/api/hr/skills/", hr,
            json={"name": name, "code": code, "category": "demo"}, expect=[201],
        ).json())

    # employee skill evaluations (manager rates their team member)
    mgr = acc["manager"]["access"]
    existing = unwrap(request("get", "core_hr", "/api/hr/employee-skills/", hr).json())
    already = {
        (e["employee"]["id"], e["skill"]["code"]) for e in existing
    }
    for code, level in EMPLOYEE_SKILLS.items():
        if (profiles["employee"]["id"], code) in already:
            continue
        request(
            "post", "core_hr", "/api/hr/employee-skills/", mgr,
            json={
                "employee_id": profiles["employee"]["id"],
                "skill_id": skills[code]["id"], "level": level,
            },
            expect=[201],
        )

    # review cycle + goal
    cycles = unwrap(request("get", "core_hr", "/api/reviews/cycles/", hr).json())
    if not any(c["name"] == "Annual Review 2026" for c in cycles):
        request(
            "post", "core_hr", "/api/reviews/cycles/", hr,
            json={
                "name": "Annual Review 2026",
                "start_date": "2026-01-01", "end_date": "2026-12-31",
            },
            expect=[201],
        )
    goals = unwrap(request("get", "core_hr", "/api/reviews/goals/", hr).json())
    if not goals:
        request(
            "post", "core_hr", "/api/reviews/goals/", hr,
            json={
                "employee_id": profiles["employee"]["id"],
                "title": "Reach Lead Developer readiness 80%",
                "description": "Close the skills gap identified by career-sim.",
            },
            expect=[201],
        )

    # wellbeing survey + one submission from the employee
    surveys = unwrap(request("get", "core_hr", "/api/wellbeing/surveys/", hr).json())
    survey = next((s for s in surveys if s["title"] == "Pulse Q3 2026"), None)
    if survey is None:
        survey = unwrap(request(
            "post", "core_hr", "/api/wellbeing/surveys/", hr,
            json={"title": "Pulse Q3 2026", "description": "Quarterly pulse."},
            expect=[201],
        ).json())
        q1 = unwrap(request(
            "post", "core_hr", f"/api/wellbeing/surveys/{survey['id']}/questions/", hr,
            json={"text": "How is your work-life balance?", "type": "SCALE_1_5", "order": 1},
            expect=[201],
        ).json())
        q2 = unwrap(request(
            "post", "core_hr", f"/api/wellbeing/surveys/{survey['id']}/questions/", hr,
            json={"text": "Do you feel supported by your manager?", "type": "YES_NO", "order": 2},
            expect=[201],
        ).json())
        request(
            "post", "core_hr", f"/api/wellbeing/surveys/{survey['id']}/submit/",
            acc["employee"]["access"],
            json={"answers": {str(q1["id"]): "3", str(q2["id"]): "yes"}},
            expect=[201],
        )

    return profiles


def seed_workload(acc) -> None:
    log("[workload] tasks, signal, scores")
    emp = acc["employee"]["access"]
    mgr = acc["manager"]["access"]

    existing = unwrap(request("get", "workload", "/api/workload/tasks/", emp).json())
    if not existing:
        today = date.today()
        tasks = [
            # a heavy, deadline-pressured mix -> HIGH/BURNOUT for the demo
            ("Migrate legacy shared repo", 12, 5, 1, False),
            ("Implement RS256 key rotation", 8, 4, 2, False),
            ("Fix production incident", 6, 5, 0, True),
            ("Quarterly report", 5, 3, 2, False),
            ("Code reviews backlog", 6, 3, 3, False),
            ("Onboard new intern", 4, 2, 6, False),
        ]
        for title, hours, cx, due_in, unplanned in tasks:
            request(
                "post", "workload", "/api/workload/tasks/", emp,
                json={
                    "title": title, "estimated_hours": hours, "complexity": cx,
                    "deadline": str(today + timedelta(days=due_in)),
                    "is_unplanned": unplanned,
                },
                expect=[201],
            )
        # manager assigns one more
        request(
            "post", "workload", "/api/workload/tasks/", mgr,
            json={
                "title": "Prepare sprint demo",
                "user_id": acc["employee"]["user_id"],
                "estimated_hours": 3, "complexity": 2,
                "deadline": str(today + timedelta(days=2)),
            },
            expect=[201],
        )
        request(
            "post", "workload", "/api/workload/signals/", emp,
            json={
                "date": str(today), "meetings_count": 5,
                "interruptions_count": 7, "stress_level": 4,
                "comment": "Sprint crunch",
            },
            expect=[201],
        )

    score = request("post", "workload", "/api/workload/scores/compute/", emp,
                    expect=[201]).json()
    log(f"  employee score: {score['score']} ({score['level']})"
        + (" -> ALERT raised" if score.get("alert") else ""))

    # manager sees the team overview
    request(
        "get", "workload",
        f"/api/workload/team-overview/?user_ids={acc['employee']['user_id']}",
        mgr, expect=[200],
    )


def seed_career_sim(acc) -> dict:
    log("[career-sim] demo positions + skills gap")
    hr = acc["hr"]["access"]
    emp = acc["employee"]["access"]
    positions = request(
        "post", "career_sim", "/api/career/demo-data/reset/", hr, expect=[201]
    ).json()["positions"]
    lead = next(p for p in positions if p["title"] == "Lead Developer")
    gap = request(
        "get", "career_sim",
        f"/api/career/skills-gap/?target_position_id={lead['id']}",
        emp, expect=[200],
    ).json()
    log(f"  Lead Developer readiness: {gap['readiness_percent']}% "
        f"({len(gap['skills_met'])} met / {len(gap['skills_gap'])} gaps, "
        f"market data: {gap['sources']['market_demand']})")
    return gap


def seed_policy_gen(acc) -> None:
    log("[policy-gen] analytical store + a first simulation")
    hr = acc["hr"]["access"]
    request("post", "policy_gen", "/api/policy/demo-data/reset/", hr, expect=[201])
    sim = request(
        "post", "policy_gen", "/api/policy/simulate/", hr,
        json={"policy_type": "remote_work", "magnitude": 5}, expect=[200],
    ).json()
    log(f"  remote_work@5 impact: {sim['impact']}")


def seed_retention(acc) -> None:
    log("[retention] engagement store + detection")
    hr = acc["hr"]["access"]
    # NOTE: rows for some users may already exist, auto-created by the
    # workload->retention burnout ingest — seed only the missing ones.
    existing = unwrap(request("get", "retention", "/api/retention/employees/", hr).json())
    known_user_ids = {e["user_id"] for e in existing}
    rows = [
        (acc["employee"]["user_id"], "EMP-001", "Youssef Ziani",
         acc["employee"]["email"], 45, 62, 3),   # at risk
        (acc["manager"]["user_id"], "EMP-002", "Mounir Mansouri",
         acc["manager"]["email"], 85, 80, 1),
        (acc["hr"]["user_id"], "EMP-003", "Hind Haddad",
         acc["hr"]["email"], 90, 85, 0),
    ]
    created = 0
    for user_id, eid, name, email, eng, perf, absence in rows:
        if user_id in known_user_ids:
            continue
        request(
            "post", "retention", "/api/retention/employees/", hr,
            json={
                "user_id": user_id, "employee_id": eid, "name": name,
                "email": email, "engagement_score": eng,
                "performance_score": perf, "absence_days_90d": absence,
            },
            expect=[201],
        )
        created += 1
    if created:
        detect = request("post", "retention", "/api/retention/detect/", hr,
                         expect=[201]).json()
        log(f"  detection: {detect['at_risk_count']} at-risk, "
            f"conversation(s) opened")
    else:
        log("  engagement store already seeded")
    signals = request("get", "retention", "/api/retention/signals/", hr,
                      expect=[200]).json()
    burnout = [s for s in signals if s["signal_type"] == "burnout_risk"]
    if burnout:
        log(f"  cross-service wiring: {len(burnout)} burnout signal(s) "
            f"ingested from workload")


def main() -> int:
    log("== SmartHR360 demo seed ==")
    log("[healthz] waiting for services…")
    up = wait_for_services()

    log("[auth] demo accounts")
    acc = bootstrap_accounts()

    seed_core_hr(acc)
    seed_workload(acc)
    seed_career_sim(acc)
    seed_policy_gen(acc)
    seed_retention(acc)

    log("")
    log("== Demo ready ==")
    log(f"  password for all accounts: {DEMO_PASSWORD}")
    for key in ("admin", "hr", "manager", "employee"):
        log(f"  {key:9s} {acc[key]['email']}")
    if "future_skills" not in up:
        log("  note: future-skills was not running; skills-gap market "
            "data shows 'unavailable' until it is.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StepFailed as exc:
        log(f"SEED FAILED: {exc}")
        sys.exit(1)
