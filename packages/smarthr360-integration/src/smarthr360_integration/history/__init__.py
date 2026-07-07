"""Reusable Slowly Changing Dimension (Type 2) building blocks.

A service subclasses :class:`SCD2HistoryBase`, adds its own owner FK and the
snapshotted domain fields, and calls :func:`snapshot_history` — no SCD2 logic is
re-implemented per service.
"""

from .models import SCD2HistoryBase
from .service import (
    history_signal_suppressed,
    signal_suppressed,
    snapshot_history,
)

__all__ = [
    "SCD2HistoryBase",
    "snapshot_history",
    "history_signal_suppressed",
    "signal_suppressed",
]
