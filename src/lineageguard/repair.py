from __future__ import annotations

from lineageguard.models import ChangeType, FilePatch, ImpactReport, RepairPlan


class DeterministicRepairPlanner:
    """Safe baseline planner; an LLM may enrich the explanation but not bypass validation."""

    def plan(self, report: ImpactReport) -> RepairPlan | None:
        event = report.event
        if report.score < 30:
            return None
        if event.change_type == ChangeType.COLUMN_RENAMED:
            if not event.previous_field or not event.field:
                return self._manual(report, "Column rename lacks old/new field names.")
            return RepairPlan(
                title=f"Preserve compatibility for {event.previous_field}",
                strategy="compatibility_alias",
                explanation=(
                    f"Roll back the output alias from {event.field} to the stable contract "
                    f"{event.previous_field} so production ML consumers remain operational "
                    "while a coordinated migration is reviewed."
                ),
                patches=[
                    FilePatch(
                        path="demo/dbt_project/models/staging/stg_customers.sql",
                        rationale=(
                            "Roll back the breaking output alias while downstream consumers "
                            "migrate to the new field contract."
                        ),
                        original_text=f"as {event.field}",
                        replacement_text=f"as {event.previous_field}",
                    )
                ],
            )
        return self._manual(
            report, "No deterministic repair template is available for this change."
        )

    @staticmethod
    def _manual(report: ImpactReport, reason: str) -> RepairPlan:
        return RepairPlan(
            title=f"Review {report.event.change_type.value}",
            strategy="human_review",
            explanation=reason,
            requires_human_review=True,
        )
