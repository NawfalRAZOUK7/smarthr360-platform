"""Abstract SCD Type 2 base model.

A concrete history model subclasses this, declares its own owner ForeignKey and
the snapshotted domain fields, and implements :meth:`tracked_snapshot` (the set
of fields whose change opens a new version).

Example::

    class WorkloadScoreHistory(SCD2HistoryBase):
        employee_user_id = models.PositiveBigIntegerField(db_index=True)
        score = models.FloatField()
        band = models.CharField(max_length=16)

        SCD2_OWNER_FIELDS = ("employee_user_id",)

        @property
        def tracked_snapshot(self):
            return {"score": self.score, "band": self.band}
"""

from __future__ import annotations

from django.db import models


class SCD2HistoryBase(models.Model):
    """Validity-window + provenance fields common to every SCD2 history table."""

    version = models.PositiveIntegerField(default=1)
    date_debut = models.DateTimeField(db_index=True)
    date_fin = models.DateTimeField(null=True, blank=True, db_index=True)
    is_current = models.BooleanField(default=True)

    change_reason = models.CharField(max_length=255, blank=True)
    changed_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    source_system = models.CharField(max_length=32, blank=True)

    recorded_at = models.DateTimeField(auto_now_add=True)

    #: Field names identifying the owner (used to find the open row). Override.
    SCD2_OWNER_FIELDS: tuple[str, ...] = ()

    class Meta:
        abstract = True

    @property
    def tracked_snapshot(self) -> dict:  # pragma: no cover - overridden
        raise NotImplementedError(
            "Subclasses must implement tracked_snapshot (the compared fields)."
        )

    def owner_filter(self) -> dict:
        return {f: getattr(self, f) for f in self.SCD2_OWNER_FIELDS}
