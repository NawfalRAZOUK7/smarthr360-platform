"""Standardized HTTP error envelope (JSON:API-like ``errors`` array).

Shared so every service returns the same error contract. The payload-building
logic is separated from the DRF Response so it can be unit-tested without DRF.
"""

from __future__ import annotations


def build_error_payload(status_code: int, code: str, title: str, detail: str = "") -> dict:
    return {
        "errors": [
            {
                "status": str(status_code),
                "code": code,
                "title": title,
                "detail": detail or title,
            }
        ]
    }


def error_response(status_code: int, code: str, title: str, detail: str = ""):
    from rest_framework.response import Response

    return Response(
        build_error_payload(status_code, code, title, detail), status=status_code
    )


def bad_request(code: str, detail: str):
    return error_response(400, code, "Bad Request", detail)


def forbidden(detail: str):
    return error_response(403, "forbidden", "Forbidden", detail)


def not_found(code: str, detail: str):
    return error_response(404, code, "Not Found", detail)
