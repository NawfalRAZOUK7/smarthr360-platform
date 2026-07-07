"""Shared paginated envelope (standard / version / data / links / meta).

Generalises the HR-Open pagination first written in core-hr so every service
returns an identical, self-describing paginated shape.
"""

from __future__ import annotations

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


def build_envelope(*, standard, version, data, links, meta) -> dict:
    """Pure builder, unit-testable without DRF request objects."""
    return {
        "standard": standard,
        "version": version,
        "data": data,
        "links": links,
        "meta": meta,
    }


class StandardEnvelopePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    #: Overridable per service/endpoint for a self-describing profile tag.
    standard = "SmartHR360"
    version = "1.0"

    def get_paginated_response(self, data):
        paginator = self.page.paginator
        envelope = build_envelope(
            standard=self.standard,
            version=self.version,
            data=data,
            links={
                "self": self.request.build_absolute_uri(),
                "next": self.get_next_link(),
                "prev": self.get_previous_link(),
            },
            meta={
                "totalCount": paginator.count,
                "pageCount": paginator.num_pages,
                "page": self.page.number,
                "pageSize": self.get_page_size(self.request),
            },
        )
        return Response(envelope)
