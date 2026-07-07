"""Generic SCD Type 2 snapshot service (idempotent).

Works on any concrete subclass of :class:`SCD2HistoryBase`. Given the owner
identity and the new tracked snapshot, it closes the current open version and
opens a new one only when a tracked field actually changed.

The diff (`snapshot_differs`) is pure and unit-testable without a database.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from typing import Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("smarthr360.history")

_state = threading.local()


def signal_suppressed() -> bool:
    return getattr(_state, "suppress", False)


@contextlib.contextmanager
def history_signal_suppressed():
    """Mute history post_save signals in this block (caller snapshots explicitly)."""
    previous = getattr(_state, "suppress", False)
    _state.suppress = True
    try:
        yield
    finally:
        _state.suppress = previous


def snapshot_differs(new: dict, current_snapshot: Optional[dict]) -> bool:
    """True when the new tracked snapshot differs from the current one."""
    if current_snapshot is None:
        return True
    keys = set(new) | set(current_snapshot)
    return any(new.get(k) != current_snapshot.get(k) for k in keys)


@transaction.atomic
def snapshot_history(
    history_model,
    *,
    owner_filter: dict,
    snapshot: dict,
    reason: str = "",
    changed_by_user_id: Optional[int] = None,
    source_system: str = "",
    at=None,
):
    """Open a new SCD2 version for the owner iff a tracked field changed.

    ``owner_filter`` identifies the entity (e.g. {"employee_user_id": 42}).
    ``snapshot`` is the dict of tracked fields to persist. Returns the new row,
    or ``None`` when nothing changed.
    """
    now = at or timezone.now()

    current = (
        history_model.objects.select_for_update()
        .filter(date_fin__isnull=True, **owner_filter)
        .order_by("-version")
        .first()
    )
    current_snapshot = current.tracked_snapshot if current is not None else None

    if not snapshot_differs(snapshot, current_snapshot):
        return None

    if current is not None:
        current.date_fin = now
        current.is_current = False
        current.save(update_fields=["date_fin", "is_current"])
        version = current.version + 1
        reason = reason or _describe(current_snapshot, snapshot)
    else:
        version = 1
        reason = reason or "initial"

    row = history_model.objects.create(
        version=version,
        date_debut=now,
        date_fin=None,
        is_current=True,
        change_reason=reason[:255],
        changed_by_user_id=changed_by_user_id,
        source_system=source_system,
        **owner_filter,
        **snapshot,
    )
    logger.info(
        "SCD2 snapshot %s owner=%s v%s",
        history_model.__name__,
        owner_filter,
        version,
    )
    return row


def _describe(old: dict, new: dict) -> str:
    keys = set(old or {}) | set(new or {})
    changed = [k for k in keys if (old or {}).get(k) != (new or {}).get(k)]
    return "changed: " + ", ".join(sorted(changed))
