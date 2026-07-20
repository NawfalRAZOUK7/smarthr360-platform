#!/usr/bin/env python3
"""SmartHR360 FULL demo seed — a large, realistic organisation.

Builds on seed_demo.py's approach (pure HTTP, idempotent) but at scale:

  auth        4 staff accounts + 20 employees across the org
  core-hr     6 departments, 24 profiles with manager links, 14 skills,
              ~90 skill evaluations, future-competency demand (feeds the
              skill-gap engine), 2 review cycles, 8 reviews with items,
              10 goals, 2 wellbeing surveys with 8+ responses each
              (crosses the anonymity threshold so stats are visible)
  workload    tasks + signals + computed scores for 6 employees
              (two of them overloaded -> alerts + burnout signals)
  career-sim  demo positions + skills-gap for two employees
  policy-gen  analytical store + 3 simulations
  retention   12 engagement rows, risk detection, 2 recorded outcomes

Idempotent: safe to run repeatedly (checks-before-create everywhere).
Run AFTER the stack is up:   python scripts/seed_demo_full.py
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta

import time

from platform_client import (
    DEMO_PASSWORD,
    DEMO_USERS,
    StepFailed,
    log,
    paged_get,
    request,
    unwrap,
    wait_for_services,
)


def robust_account(email, username, first, last, role) -> dict:
    """login-or-register that survives auth throttling (429) and
    'already exists' races: retries with backoff instead of dying."""
    last_error = ""
    for attempt in range(10):
        r = request("post", "auth", "/api/auth/login/",
                    json={"email": email, "password": DEMO_PASSWORD})
        if r.status_code == 200:
            body = unwrap(r.json())
            user, tokens = body.get("user", body), body.get("tokens", body)
            return {"user_id": user["id"], "email": email, "role": role,
                    "access": tokens["access"], "refresh": tokens.get("refresh")}
        if r.status_code == 429:
            wait = 8 * (attempt + 1)
            log(f"  [auth] throttled on login for {email} — waiting {wait}s")
            time.sleep(wait)
            continue
        # login rejected for another reason -> try to register
        r2 = request("post", "auth", "/api/auth/register/",
                     json={"email": email, "username": username,
                           "first_name": first, "last_name": last,
                           "password": DEMO_PASSWORD, "role": role})
        if r2.status_code == 201:
            body = unwrap(r2.json())
            user, tokens = body.get("user", body), body.get("tokens", body)
            return {"user_id": user["id"], "email": email, "role": role,
                    "access": tokens["access"], "refresh": tokens.get("refresh")}
        if r2.status_code == 429:
            wait = 8 * (attempt + 1)
            log(f"  [auth] throttled on register for {email} — waiting {wait}s")
            time.sleep(wait)
            continue
        # exists but login failed (likely login throttle window) -> backoff
        last_error = f"login {r.status_code} / register {r2.status_code}: {r2.text[:150]}"
        time.sleep(5)
    raise StepFailed(f"could not obtain account {email}: {last_error}")


def robust_bootstrap() -> dict:
    accounts = {}
    for key, email, username, first, last, role in DEMO_USERS:
        accounts[key] = robust_account(email, username, first, last, role)
        log(f"  [auth] {key}: user_id={accounts[key]['user_id']} role={role}")
    return accounts

random.seed(42)  # deterministic volume data


# --------------------------------------------------------------------------
# The organisation
# --------------------------------------------------------------------------

DEPARTMENTS = [
    ("Engineering", "ENG"),
    ("Data & AI", "DATA"),
    ("Human Resources", "HR"),
    ("Finance", "FIN"),
    ("Sales", "SALES"),
    ("Product", "PROD"),
]

SKILLS = [
    ("Python", "PY", "tech"), ("Django", "DJ", "tech"),
    ("Kubernetes", "K8S", "tech"), ("SQL", "SQL", "tech"),
    ("Machine Learning", "ML", "tech"), ("MLOps", "MLOPS", "tech"),
    ("Security Engineering", "SEC", "tech"), ("Git & CI/CD", "GIT", "tech"),
    ("Communication", "COMM", "soft"), ("Negotiation", "NEG", "soft"),
    ("Project Management", "PM", "business"),
    ("People Analytics", "PA", "business"),
    ("Financial Modelling", "FMOD", "business"),
    ("Process Automation", "AUTO", "business"),
]

# (first, last, dept, title, skills{code: level 1-4})
PEOPLE = [
    ("Yasmine", "Alaoui", "ENG", "Backend Engineer", {"PY": 4, "DJ": 3, "SQL": 3, "GIT": 4}),
    ("Karim", "Bennis", "ENG", "Backend Engineer", {"PY": 3, "DJ": 3, "K8S": 2, "GIT": 3}),
    ("Sara", "Chraibi", "ENG", "DevOps Engineer", {"K8S": 3, "GIT": 4, "SEC": 2, "PY": 2}),
    ("Omar", "Drissi", "ENG", "Frontend Engineer", {"GIT": 3, "COMM": 3, "PY": 1}),
    ("Nadia", "El Fassi", "ENG", "Security Engineer", {"SEC": 3, "K8S": 2, "PY": 3}),
    ("Hamza", "Fikri", "DATA", "Data Scientist", {"ML": 3, "PY": 4, "SQL": 3}),
    ("Lina", "Guessous", "DATA", "Data Engineer", {"SQL": 4, "PY": 3, "MLOPS": 1, "K8S": 2}),
    ("Adam", "Hajji", "DATA", "ML Engineer", {"ML": 3, "MLOPS": 2, "PY": 4}),
    ("Rita", "Idrissi", "DATA", "Analytics Engineer", {"SQL": 4, "PA": 2, "COMM": 3}),
    ("Mehdi", "Jabri", "HR", "HR Officer", {"COMM": 4, "PA": 2, "PM": 2}),
    ("Salma", "Kadiri", "HR", "Talent Partner", {"COMM": 4, "NEG": 3, "PA": 1}),
    ("Youssef", "Lamrani", "FIN", "Financial Analyst", {"FMOD": 3, "SQL": 2, "AUTO": 1}),
    ("Imane", "Mekouar", "FIN", "Senior Accountant", {"FMOD": 4, "AUTO": 2}),
    ("Anas", "Naciri", "FIN", "Controller", {"FMOD": 3, "PM": 3, "SQL": 2}),
    ("Kenza", "Ouazzani", "SALES", "Account Executive", {"NEG": 3, "COMM": 4}),
    ("Reda", "Qadiri", "SALES", "Account Executive", {"NEG": 2, "COMM": 3}),
    ("Dounia", "Rhazi", "SALES", "Sales Ops", {"SQL": 2, "AUTO": 2, "COMM": 3}),
    ("Ilyas", "Sefrioui", "PROD", "Product Manager", {"PM": 4, "COMM": 4, "SQL": 1}),
    ("Aya", "Tazi", "PROD", "Product Designer", {"COMM": 3, "PM": 2}),
    ("Zakaria", "Ziani", "PROD", "Product Analyst", {"SQL": 3, "PA": 2, "PM": 2}),
]

# Future demand per department: (dept, skill, timeframe, importance 1-5).
# The skill-gap engine maps importance -> required proficiency level.
FUTURE_NEEDS = [
    ("ENG", "K8S", "SHORT", 5), ("ENG", "SEC", "SHORT", 4), ("ENG", "PY", "MEDIUM", 3),
    ("DATA", "MLOPS", "SHORT", 5), ("DATA", "ML", "MEDIUM", 4),
    ("HR", "PA", "MEDIUM", 4), ("FIN", "AUTO", "MEDIUM", 4),
    ("SALES", "NEG", "MEDIUM", 3), ("PROD", "PA", "LONG", 3),
]


def seed_people(acc) -> tuple[dict, dict, dict]:
    """Departments, 20+4 profiles, skills, evaluations, future needs."""
    hr = acc["hr"]["access"]
    log("[core-hr] big org: departments, 24 profiles, skills, evaluations")

    # -- departments
    departments = {}
    existing = unwrap(request("get", "core_hr", "/api/hr/departments/", hr).json())
    by_code = {d["code"]: d for d in existing}
    for name, code in DEPARTMENTS:
        departments[code] = by_code.get(code) or unwrap(request(
            "post", "core_hr", "/api/hr/departments/", hr,
            json={"name": name, "code": code}, expect=[201],
        ).json())

    # -- staff accounts (reuse seed_demo's 4) + 20 employees
    people_acc = {}
    for i, (first, last, dept, title, _skills) in enumerate(PEOPLE, start=1):
        key = f"emp{i:02d}"
        email = f"{first.lower()}.{last.lower().replace(' ', '')}@demo.smarthr360.dev"
        people_acc[key] = robust_account(
            email, f"demo-{key}", first, last, "EMPLOYEE"
        )
    log(f"  accounts: 4 staff + {len(people_acc)} employees (password: {DEMO_PASSWORD})")

    # -- profiles (idempotent by user_id; auth provisioning may have
    #    auto-created bare profiles at registration, and the list is
    #    paginated — fetch ALL pages)
    existing = paged_get("core_hr", "/api/hr/employees/", hr)
    by_user = {p["user_id"]: p for p in existing}
    manager_profile_id = None
    # ensure the 4 staff profiles exist first (as in seed_demo)
    staff_plan = [
        ("hr", "HR", "HR Business Partner"),
        ("manager", "ENG", "Engineering Manager"),
        ("employee", "ENG", "Software Developer"),
        ("admin", "HR", "Platform Administrator"),
    ]
    for key, dept, title in staff_plan:
        a = acc[key]
        if a["user_id"] not in by_user:
            by_user[a["user_id"]] = unwrap(request(
                "post", "core_hr", "/api/hr/employees/", hr,
                json={
                    "user_id": a["user_id"], "email": a["email"],
                    "first_name": key.title(), "user_role": a["role"],
                    "job_title": title,
                    "department_id": departments[dept]["id"],
                    "hire_date": str(date.today() - timedelta(days=900)),
                },
                expect=[201],
            ).json())
    manager_profile_id = by_user[acc["manager"]["user_id"]]["id"]

    profiles = {}
    for i, (first, last, dept, title, _skills) in enumerate(PEOPLE, start=1):
        key = f"emp{i:02d}"
        a = people_acc[key]
        payload = {
            "user_id": a["user_id"], "email": a["email"],
            "first_name": first, "last_name": last,
            "user_role": "EMPLOYEE", "job_title": title,
            "department_id": departments[dept]["id"],
            "hire_date": str(date.today() - timedelta(days=random.randint(120, 2000))),
        }
        if dept == "ENG":
            payload["manager_id"] = manager_profile_id
        if a["user_id"] in by_user:
            # profile exists (auth provisioning) — enrich with org data
            prof = by_user[a["user_id"]]
            patch = {k: v for k, v in payload.items()
                     if k in ("department_id", "manager_id", "job_title",
                              "hire_date", "first_name", "last_name")}
            profiles[key] = unwrap(request(
                "patch", "core_hr", f"/api/hr/employees/{prof['id']}/",
                hr, json=patch, expect=[200],
            ).json())
        else:
            profiles[key] = unwrap(request(
                "post", "core_hr", "/api/hr/employees/", hr,
                json=payload, expect=[201],
            ).json())
    log(f"  profiles: {len(profiles)} employees across {len(DEPARTMENTS)} departments")

    # -- skills catalog
    skills = {}
    existing = paged_get("core_hr", "/api/hr/skills/", hr)
    by_code = {s["code"]: s for s in existing}
    for name, code, category in SKILLS:
        skills[code] = by_code.get(code) or unwrap(request(
            "post", "core_hr", "/api/hr/skills/", hr,
            json={"name": name, "code": code, "category": category}, expect=[201],
        ).json())

    # -- evaluations (~90; paginated)
    existing = paged_get("core_hr", "/api/hr/employee-skills/", hr)
    already = {(e["employee"]["id"], e["skill"]["code"]) for e in existing}
    created = 0
    for i, (_f, _l, _d, _t, own_skills) in enumerate(PEOPLE, start=1):
        prof = profiles[f"emp{i:02d}"]
        for code, level in own_skills.items():
            if (prof["id"], code) in already:
                continue
            request(
                "post", "core_hr", "/api/hr/employee-skills/", hr,
                json={"employee_id": prof["id"],
                      "skill_id": skills[code]["id"], "level": level},
                expect=[201],
            )
            created += 1
    log(f"  skill evaluations: +{created}")

    # -- future competency demand (what the skill-gap engine forecasts against)
    existing = paged_get("core_hr", "/api/hr/future-competencies/", hr)
    have = set()
    for fc in existing:
        d = fc.get("department") or {}
        s = fc.get("skill") or {}
        have.add((d.get("code"), s.get("code")))
    created, errors = 0, []
    for dept, skill_code, timeframe, importance in FUTURE_NEEDS:
        if (dept, skill_code) in have:
            continue
        r = request(
            "post", "core_hr", "/api/hr/future-competencies/", hr,
            json={
                "department_id": departments[dept]["id"],
                "skill_id": skills[skill_code]["id"],
                "timeframe": timeframe, "importance": importance,
                "description": "seeded demand (full demo)",
            },
        )
        if r.status_code == 201:
            created += 1
        else:
            errors.append(f"{dept}/{skill_code}: {r.status_code} {r.text[:120]}")
    log(f"  future competency needs: +{created}"
        + (f" ({len(errors)} failed: {errors[0]})" if errors else ""))

    return departments, profiles, people_acc


def seed_reviews(acc, profiles) -> None:
    hr = acc["hr"]["access"]
    log("[core-hr] review cycles, reviews with items, goals")

    cycles = paged_get("core_hr", "/api/reviews/cycles/", hr)
    by_name = {c["name"]: c for c in cycles}
    wanted = [
        ("Annual Review 2026", "2026-01-01", "2026-12-31"),
        ("Mid-year Check 2026", "2026-06-01", "2026-07-31"),
    ]
    for name, start, end in wanted:
        if name not in by_name:
            by_name[name] = unwrap(request(
                "post", "core_hr", "/api/reviews/cycles/", hr,
                json={"name": name, "start_date": start, "end_date": end},
                expect=[201],
            ).json())
    annual = by_name["Annual Review 2026"]

    reviews = paged_get("core_hr", "/api/reviews/", hr)
    reviewed_emp_ids = {(r.get("employee") or {}).get("id") for r in reviews}
    criteria = ["Technical delivery", "Collaboration", "Autonomy", "Impact"]
    created = 0
    for key in list(profiles)[:8]:
        prof = profiles[key]
        if prof["id"] in reviewed_emp_ids:
            continue
        r = request(
            "post", "core_hr", "/api/reviews/", hr,
            json={"employee_id": prof["id"], "cycle_id": annual["id"]},
        )
        if r.status_code != 201:
            continue
        review = unwrap(r.json())
        for crit in random.sample(criteria, k=3):
            request(
                "post", "core_hr", f"/api/reviews/{review['id']}/items/", hr,
                json={"criteria": crit, "score": random.randint(3, 5),
                      "comment": "Seeded evaluation."},
            )
        request("post", "core_hr", f"/api/reviews/{review['id']}/submit/", hr)
        created += 1
    log(f"  reviews: +{created} (with items, submitted)")

    goals = paged_get("core_hr", "/api/reviews/goals/", hr)
    if len(goals) < 10:
        titles = [
            "Close the K8s gap to level 3", "Ship MLOps pipeline v1",
            "Automate monthly reporting", "Mentor one junior",
            "Lead a cross-team initiative", "Reduce incident MTTR by 20%",
            "Complete security certification", "Improve NPS follow-up loop",
            "Document the data catalog", "Prepare promotion case",
        ]
        for key, title in zip(list(profiles)[:10], titles):
            request(
                "post", "core_hr", "/api/reviews/goals/", hr,
                json={"employee_id": profiles[key]["id"],
                      "cycle_id": annual["id"],
                      "title": title,
                      "description": "Seeded goal (full demo)."},
            )
        log("  goals: topped up to 10")


def seed_wellbeing(acc, people_acc) -> None:
    hr = acc["hr"]["access"]
    log("[core-hr] wellbeing: 2 surveys, 8+ responses each (stats visible)")

    surveys = paged_get("core_hr", "/api/wellbeing/surveys/", hr)
    by_title = {s["title"]: s for s in surveys}

    def ensure_survey(title, description, questions):
        if title in by_title:
            return by_title[title]
        s = unwrap(request(
            "post", "core_hr", "/api/wellbeing/surveys/", hr,
            json={"title": title, "description": description}, expect=[201],
        ).json())
        s["questions"] = []
        for i, (text, qtype) in enumerate(questions, start=1):
            q = unwrap(request(
                "post", "core_hr", f"/api/wellbeing/surveys/{s['id']}/questions/", hr,
                json={"text": text, "type": qtype, "order": i}, expect=[201],
            ).json())
            s["questions"].append(q)
        by_title[title] = s
        return s

    pulse = ensure_survey(
        "Pulse Q3 2026", "Quarterly wellbeing pulse.",
        [("How is your work-life balance?", "SCALE_1_5"),
         ("Do you feel supported by your manager?", "YES_NO"),
         ("Anything else you want to share?", "TEXT")],
    )
    remote = ensure_survey(
        "Remote work check-in", "How is hybrid working going?",
        [("Rate your home-office setup", "SCALE_1_5"),
         ("Do you have enough social contact with the team?", "YES_NO")],
    )

    # submissions from the first 9 employee accounts (once each; API rejects dupes)
    responders = list(people_acc.values())[:9]
    for survey in (pulse, remote):
        qs = survey.get("questions") or unwrap(request(
            "get", "core_hr", f"/api/wellbeing/surveys/{survey['id']}/", hr
        ).json()).get("questions", [])
        if not qs:
            continue
        submitted = 0
        for person in responders:
            answers = {}
            for q in qs:
                if q["type"] == "SCALE_1_5":
                    answers[str(q["id"])] = str(random.randint(2, 5))
                elif q["type"] == "YES_NO":
                    answers[str(q["id"])] = random.choice(["yes", "yes", "no"])
                else:
                    answers[str(q["id"])] = random.choice(
                        ["More focus time please.", "All good!", "Better coffee."]
                    )
            r = request(
                "post", "core_hr",
                f"/api/wellbeing/surveys/{survey['id']}/submit/",
                person["access"], json={"answers": answers},
            )
            submitted += int(r.status_code == 201)
        log(f"  '{survey['title']}': +{submitted} responses")


def seed_workload_volume(acc, people_acc) -> None:
    log("[workload] tasks + signals + scores for 6 employees")
    heavy = {"emp01", "emp07"}          # will trend to burnout
    sample = ["emp01", "emp02", "emp06", "emp07", "emp12", "emp15"]
    today = date.today()

    for key in sample:
        person = people_acc[key]
        tok = person["access"]
        existing = unwrap(request("get", "workload", "/api/workload/tasks/", tok).json())
        if not existing:
            n = 6 if key in heavy else 3
            for t in range(n):
                request(
                    "post", "workload", "/api/workload/tasks/", tok,
                    json={
                        "title": f"Seeded task {t + 1}",
                        "estimated_hours": random.randint(6, 12) if key in heavy else random.randint(2, 5),
                        "complexity": random.randint(4, 5) if key in heavy else random.randint(1, 3),
                        "deadline": str(today + timedelta(days=random.randint(0, 3 if key in heavy else 10))),
                        "is_unplanned": key in heavy and t == 0,
                    },
                    expect=[201],
                )
            request(
                "post", "workload", "/api/workload/signals/", tok,
                json={
                    "date": str(today),
                    "meetings_count": 6 if key in heavy else 2,
                    "interruptions_count": 8 if key in heavy else 2,
                    "stress_level": 5 if key in heavy else 2,
                    "comment": "seeded",
                },
                expect=[201],
            )
        score = request("post", "workload", "/api/workload/scores/compute/", tok,
                        expect=[201]).json()
        log(f"  {key}: score {score.get('score')} ({score.get('level')})")


def seed_retention_volume(acc, people_acc) -> None:
    """Full retention story: engagement rows -> detection (opens
    conversations) -> complete each conversation so a pending ACTION is
    generated -> approve some and record outcomes. Leaves at least one
    pending action so the UI approve/reject/outcome workflow has data.
    """
    hr = acc["hr"]["access"]
    log("[retention] engagement rows + detection + conversations -> actions")
    existing = paged_get("retention", "/api/retention/employees/", hr)
    known = {e["user_id"] for e in existing}

    # First 3 employees are engineered CRITICAL (very low engagement +
    # poor performance + high absence) so detection reliably fires.
    rows = []
    for i, key in enumerate(list(people_acc)[:12], start=1):
        p = people_acc[key]
        at_risk = i <= 3
        rows.append((
            p["user_id"], f"EMP-{100 + i}", key, p["email"],
            random.randint(20, 35) if at_risk else random.randint(65, 95),
            random.randint(35, 48) if at_risk else random.randint(65, 95),
            random.randint(9, 14) if at_risk else random.randint(0, 3),
        ))
    # A dedicated 13th always-critical employee. Because it is a distinct
    # user_id, a fresh run (even against an already-seeded DB) creates a
    # new signal -> conversation -> action, guaranteeing at least one
    # PENDING action for the UI approve/reject/outcome workflow.
    if len(people_acc) >= 13:
        k13 = list(people_acc)[12]
        p13 = people_acc[k13]
        rows.append((p13["user_id"], "EMP-113", k13, p13["email"], 22, 40, 11))
    created = 0
    for user_id, eid, name, email, eng, perf, absence in rows:
        if user_id in known:
            continue
        request(
            "post", "retention", "/api/retention/employees/", hr,
            json={"user_id": user_id, "employee_id": eid, "name": name,
                  "email": email, "engagement_score": eng,
                  "performance_score": perf, "absence_days_90d": absence},
            expect=[201],
        )
        created += 1

    # Detection opens a conversation per at-risk employee. Idempotent:
    # if we've already run it, /detect/ simply finds signals already
    # resolved and opens nothing new.
    detect = request("post", "retention", "/api/retention/detect/", hr,
                     expect=[201]).json()
    conv_ids = [r["conversation_id"] for r in detect.get("results", [])]
    log(f"  detection: {detect.get('at_risk_count')} at-risk, "
        f"{len(conv_ids)} conversation(s) opened")

    # Complete each open conversation with a need-bearing reply so a
    # pending ACTION is generated. Keyword 'surchargé/stress/burnout'
    # -> workload need (see chatbot._extract_need_simple).
    completed = 0
    replies = [
        "Je suis vraiment surchargé, trop de stress et au bord du burnout.",
        "J'aimerais évoluer, une promotion ou une vraie perspective de carrière.",
        "Je ne me sens pas assez valorisé ni reconnu pour mon travail.",
    ]
    for idx, cid in enumerate(conv_ids):
        r = request("post", "retention",
                    f"/api/retention/conversations/{cid}/respond/", hr,
                    json={"message": replies[idx % len(replies)]})
        if r.status_code == 200 and r.json().get("completed"):
            completed += 1
    if completed:
        log(f"  conversations completed -> {completed} action(s) generated")

    # Work the action queue but ALWAYS leave the most recent pending
    # action untouched, so the UI approve/reject/outcome workflow has
    # something live to act on. Oldest-first so the newest stays pending.
    actions = paged_get("retention", "/api/retention/actions/", hr)
    pending = sorted(
        [a for a in actions if a.get("status") == "pending"],
        key=lambda a: a["id"],
    )
    to_work = pending[:-1]  # everything except the newest
    worked = 0
    for i, a in enumerate(to_work):
        rev = request("post", "retention",
                      f"/api/retention/actions/{a['id']}/review/", hr,
                      json={"status": "approved"})
        if rev.status_code != 200:
            continue
        request("post", "retention",
                f"/api/retention/actions/{a['id']}/outcome/", hr,
                json={"retained": i % 2 == 0,
                      "note": "seeded outcome (full demo)"})
        worked += 1
    left_pending = len(pending) - worked
    log(f"  actions: {worked} approved+recorded, "
        f"{left_pending} left pending for the UI")


def seed_career_and_policy(acc, people_acc) -> None:
    hr = acc["hr"]["access"]
    log("[career-sim] positions + gaps · [policy-gen] store + simulations")
    request("post", "career_sim", "/api/career/demo-data/reset/", hr, expect=[201])
    positions = request("get", "career_sim", "/api/career/positions/", hr,
                        expect=[200]).json().get("positions", [])
    if positions:
        target = positions[0]["id"]
        for key in ("emp01", "emp06"):
            request(
                "get", "career_sim",
                f"/api/career/skills-gap/?target_position_id={target}",
                people_acc[key]["access"],
            )

    request("post", "policy_gen", "/api/policy/demo-data/reset/", hr, expect=[201])
    for ptype, mag in (("remote_work", 5), ("flexible_hours", 7), ("training_budget", 4)):
        request("post", "policy_gen", "/api/policy/simulate/", hr,
                json={"policy_type": ptype, "magnitude": mag})
    log("  3 policy simulations stored")


def main() -> int:
    log("== SmartHR360 FULL demo seed ==")
    wait_for_services()
    acc = robust_bootstrap()

    departments, profiles, people_acc = seed_people(acc)
    seed_reviews(acc, profiles)
    seed_wellbeing(acc, people_acc)
    seed_workload_volume(acc, people_acc)
    seed_career_and_policy(acc, people_acc)
    seed_retention_volume(acc, people_acc)

    log("")
    log("== FULL demo ready ==")
    log(f"  password for all accounts: {DEMO_PASSWORD}")
    for key in ("admin", "hr", "manager", "employee"):
        log(f"  {key:9s} {acc[key]['email']}")
    log(f"  + {len(people_acc)} employee accounts "
        f"(e.g. {list(people_acc.values())[0]['email']})")
    log("  note: future-skills (m3) data comes from its own train/predict "
        "pipeline — run its training endpoint to populate predictions.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StepFailed as exc:
        log(f"SEED FAILED: {exc}")
        sys.exit(1)
