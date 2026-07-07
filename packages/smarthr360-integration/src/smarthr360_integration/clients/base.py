"""Base HTTP client for service-to-service calls.

Thin wrapper over ``requests`` with: a base URL, JWT propagation, sane timeout,
and uniform error handling. URL/param building is separated so it can be
unit-tested without performing real HTTP.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode


class ServiceClientError(Exception):
    """Raised on transport errors or non-2xx responses from a peer service."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


class ServiceClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        timeout: float = 5.0,
        session: Any = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._session = session  # inject a requests.Session or a fake in tests

    # -- pure helpers (unit-testable) ----------------------------------
    def build_url(self, path: str, params: Optional[dict] = None) -> str:
        url = f"{self.base_url}/{path.lstrip('/')}"
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        if clean:
            url = f"{url}?{urlencode(clean)}"
        return url

    def headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # -- transport ------------------------------------------------------
    def _session_obj(self):
        if self._session is None:
            import requests

            self._session = requests.Session()
        return self._session

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        url = self.build_url(path, params)
        try:
            resp = self._session_obj().get(
                url, headers=self.headers(), timeout=self.timeout
            )
        except Exception as exc:  # noqa: BLE001 - normalize transport errors
            raise ServiceClientError(f"GET {url} failed: {exc}") from exc

        if not (200 <= resp.status_code < 300):
            raise ServiceClientError(
                f"GET {url} -> HTTP {resp.status_code}", status=resp.status_code
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise ServiceClientError(f"GET {url} returned non-JSON") from exc
