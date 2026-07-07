"""Client for smarthr360-core-hr — the owner of employee & competency data.

Other services call these methods instead of duplicating employees, skills or
the SCD2 profile history. Endpoints target core-hr's HR + interop APIs
(Étapes 1–4).
"""

from __future__ import annotations

from typing import Optional

from .base import ServiceClient


class CoreHRClient(ServiceClient):
    """Read-only access to core-hr's public HR / interop endpoints."""

    # --- HR-Open interoperability (Étape 3) ----------------------------
    def person_competencies(
        self,
        *,
        department: Optional[str] = None,
        skill: Optional[str] = None,
        employee_id: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> dict:
        """PersonCompetency records (HR-Open shape)."""
        return self.get(
            "/api/hr/interop/person-competencies/",
            {
                "department": department,
                "skill": skill,
                "employee_id": employee_id,
                "page": page,
                "page_size": page_size,
            },
        )

    def competency_definitions(
        self, *, category: Optional[str] = None, active: Optional[bool] = None
    ) -> dict:
        return self.get(
            "/api/hr/interop/competency-definitions/",
            {
                "category": category,
                "active": None if active is None else str(bool(active)).lower(),
            },
        )

    def position_competency_models(self, *, department: Optional[str] = None) -> dict:
        return self.get(
            "/api/hr/interop/position-competency-models/",
            {"department": department},
        )

    # --- Predictions (Étape 4) -----------------------------------------
    def skill_gaps(
        self, *, department: Optional[str] = None, horizon_months: Optional[int] = None
    ) -> dict:
        return self.get(
            "/api/hr/predictions/skill-gaps/",
            {"department": department, "horizon_months": horizon_months},
        )

    # --- Organisation --------------------------------------------------
    def org_chart(self) -> dict:
        return self.get("/api/hr/org-chart/")
