"""Shared helpers for seed/e2e scripts: service URLs, auth, envelopes.

Service base URLs come from env (SMARTHR_<NAME>_URL); defaults match
docker-compose port mappings on localhost.
"""

from __future__ import annotations

import os
import time

import requests

# One session for all calls; ignore environment proxies (CI runners and
# sandboxes often define HTTP(S)_PROXY that would break localhost calls).
SESSION = requests.Session()
SESSION.trust_env = False

TIMEOUT = 10

SERVICES = {
    "auth": os.environ.get("SMARTHR_AUTH_URL", "http://localhost:8000"),
    "core_hr": os.environ.get("SMARTHR_CORE_HR_URL", "http://localhost:8001"),
    "career_sim": os.environ.get("SMARTHR_CAREER_SIM_URL", "http://localhost:8003"),
    "future_skills": os.environ.get("SMARTHR_FUTURE_SKILLS_URL", "http://localhost:8004"),
    "workload": os.environ.get("SMARTHR_WORKLOAD_URL", "http://localhost:8005"),
    "policy_gen": os.environ.get("SMARTHR_POLICY_GEN_URL", "http://localhost:8006"),
    "retention": os.environ.get("SMARTHR_RETENTION_URL", "http://localhost:8007"),
}

# future-skills is optional for the demo (heavy service); scripts degrade.
OPTIONAL_SERVICES = {"future_skills"}

DEMO_PASSWORD = os.environ.get("SMARTHR_DEMO_PASSWORD", "Demo#2026!hr360")

DEMO_USERS = [
    # key, email, username, first, last, role
    ("admin", "admin@demo.smarthr360.dev", "demo-admin", "Ada", "Admin", "ADMIN"),
    ("hr", "hr@demo.smarthr360.dev", "demo-hr", "Hind", "Haddad", "HR"),
    ("manager", "manager@demo.smarthr360.dev", "demo-manager", "Mounir", "Mansouri", "MANAGER"),
    ("employee", "employee@demo.smarthr360.dev", "demo-employee", "Youssef", "Ziani", "EMPLOYEE"),
]


class StepFailed(Exception):
    pass


def log(msg: str) -> None:
    print(msg, flush=True)


def unwrap(payload):
    """Tolerate the ApiResponseMixin envelope ({data, meta}) and
    paginated shapes ({results} / {data:{results}})."""
    if isinstance(payload, dict):
        if "data" in payload and ("meta" in payload or len(payload) == 1):
            payload = payload["data"]
        if isinstance(payload, dict) and "results" in payload:
            return payload["results"]
    return payload


def request(method, service, path, token=None, expect=None, **kwargs):
    url = f"{SERVICES[service]}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = SESSION.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
    if expect and resp.status_code not in expect:
        raise StepFailed(
            f"{method} {url} -> {resp.status_code} (expected {expect}): "
            f"{resp.text[:300]}"
        )
    return resp


def wait_for_services(names=None, tries=int(os.environ.get("SMARTHR_WAIT_TRIES", 60)), delay=int(os.environ.get("SMARTHR_WAIT_DELAY", 2))) -> list[str]:
    """Wait for /healthz/ on each service; return the ones that are up."""
    names = names or list(SERVICES)
    up: list[str] = []
    for name in names:
        ok = False
        for _ in range(tries):
            try:
                r = SESSION.get(f"{SERVICES[name]}/healthz/", timeout=3)
                if r.status_code == 200:
                    ok = True
                    break
            except requests.RequestException:
                pass
            time.sleep(delay)
        if ok:
            log(f"  [up] {name} ({SERVICES[name]})")
            up.append(name)
        elif name in OPTIONAL_SERVICES:
            log(f"  [skip] {name} not reachable (optional)")
        else:
            raise StepFailed(f"service '{name}' not reachable at {SERVICES[name]}")
    return up


def login_or_register(email, username, first, last, role) -> dict:
    """Return {user_id, access, refresh} for a demo account (idempotent)."""
    r = request(
        "post", "auth", "/api/auth/login/",
        json={"email": email, "password": DEMO_PASSWORD},
    )
    if r.status_code != 200:
        r = request(
            "post", "auth", "/api/auth/register/",
            json={
                "email": email, "username": username, "first_name": first,
                "last_name": last, "password": DEMO_PASSWORD, "role": role,
            },
            expect=[201],
        )
    body = unwrap(r.json())
    user = body.get("user", body)
    tokens = body.get("tokens", body)
    return {
        "user_id": user["id"],
        "email": email,
        "role": role,
        "access": tokens["access"],
        "refresh": tokens.get("refresh"),
    }


def bootstrap_accounts() -> dict:
    accounts = {}
    for key, email, username, first, last, role in DEMO_USERS:
        accounts[key] = login_or_register(email, username, first, last, role)
        log(f"  [auth] {key}: user_id={accounts[key]['user_id']} role={role}")
    return accounts
