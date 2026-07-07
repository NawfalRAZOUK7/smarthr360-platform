"""Idempotent Prometheus metric factories.

``django-prometheus`` already exposes the default registry at ``/metrics``.
Defining a metric twice (e.g. on autoreload, or if two modules import the same
name) raises ``ValueError: Duplicated timeseries``. These helpers return the
*existing* collector when the name is already registered, so services can define
their metrics at import time without guarding against reloads.

Naming convention: ``smarthr360_<subsystem>_<unit>``; ``_total`` for counters,
``_seconds`` for timestamps.
"""

from __future__ import annotations

from typing import Iterable

from prometheus_client import REGISTRY, Counter, Gauge, Histogram

_NS = "smarthr360"


def _full_name(name: str) -> str:
    return name if name.startswith(f"{_NS}_") else f"{_NS}_{name}"


def _existing(name: str):
    """Return an already-registered collector for ``name`` (or None).

    Counters register their base name as ``<name>_total`` internally, so we
    check the map that prometheus_client maintains of names -> collector.
    """
    mapping = getattr(REGISTRY, "_names_to_collectors", {})
    for candidate in (name, f"{name}_total", f"{name}_created"):
        if candidate in mapping:
            return mapping[candidate]
    return None


def get_counter(name: str, documentation: str, labelnames: Iterable[str] = ()) -> Counter:
    full = _full_name(name)
    existing = _existing(full)
    if isinstance(existing, Counter):
        return existing
    return Counter(full, documentation, list(labelnames))


def get_gauge(name: str, documentation: str, labelnames: Iterable[str] = ()) -> Gauge:
    full = _full_name(name)
    existing = _existing(full)
    if isinstance(existing, Gauge):
        return existing
    return Gauge(full, documentation, list(labelnames))


def get_histogram(
    name: str,
    documentation: str,
    labelnames: Iterable[str] = (),
    buckets: Iterable[float] | None = None,
) -> Histogram:
    full = _full_name(name)
    existing = _existing(full)
    if isinstance(existing, Histogram):
        return existing
    kwargs = {"labelnames": list(labelnames)}
    if buckets is not None:
        kwargs["buckets"] = tuple(buckets)
    return Histogram(full, documentation, **kwargs)
