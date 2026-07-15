from __future__ import annotations

from collections.abc import Iterable

from lineageguard.models import (
    ChangeEvent,
    ChangeType,
    ImpactContext,
    ImpactReport,
    RiskSignal,
    Severity,
)

BREAKING_CHANGES = {
    ChangeType.COLUMN_REMOVED,
    ChangeType.COLUMN_RENAMED,
    ChangeType.TYPE_CHANGED,
    ChangeType.NULLABILITY_CHANGED,
}


class RiskEngine:
    """A deterministic, explainable risk model whose output is safe to gate automation on."""

    def assess(self, event: ChangeEvent, context: ImpactContext) -> ImpactReport:
        signals = list(self._signals(event, context))
        score = min(sum(signal.points for signal in signals), 100)
        severity, decision = self._classify(score)
        summary = self._summary(event, context, severity, score)
        return ImpactReport(
            event=event,
            severity=severity,
            score=score,
            decision=decision,
            summary=summary,
            signals=signals,
            context=context,
        )

    def _signals(self, event: ChangeEvent, context: ImpactContext) -> Iterable[RiskSignal]:
        if event.change_type in BREAKING_CHANGES:
            yield RiskSignal(
                code="breaking_change",
                label="Breaking schema change",
                points=35,
                evidence=[event.change_type.value, event.field or "unknown field"],
            )
        elif event.change_type in {ChangeType.FRESHNESS_FAILED, ChangeType.PII_EXPOSURE}:
            yield RiskSignal(
                code="operational_failure",
                label="Operational or governance failure",
                points=25,
                evidence=[event.change_type.value],
            )

        if context.affected_features:
            yield RiskSignal(
                code="ml_feature_impact",
                label="ML features depend on the changed asset",
                points=25,
                evidence=[entity.urn for entity in context.affected_features],
            )

        if context.affected_deployments:
            yield RiskSignal(
                code="production_impact",
                label="Production model deployments are affected",
                points=20,
                evidence=[entity.urn for entity in context.affected_deployments],
            )
        elif context.affected_models:
            yield RiskSignal(
                code="model_impact",
                label="ML models are affected",
                points=12,
                evidence=[entity.urn for entity in context.affected_models],
            )

        sensitive_tags = sorted(
            tag
            for tag in context.governance_tags
            if tag.lower() in {"pii", "sensitive", "restricted", "regulated"}
        )
        if sensitive_tags:
            yield RiskSignal(
                code="governance_impact",
                label="Sensitive or regulated data is involved",
                points=10,
                evidence=sensitive_tags,
            )

        if context.usage_score >= 0.7:
            yield RiskSignal(
                code="high_usage",
                label="High-usage asset",
                points=10,
                evidence=[f"usage_score={context.usage_score:.2f}"],
            )
        elif not context.changed_asset.owners:
            yield RiskSignal(
                code="missing_owner",
                label="No owner is available for escalation",
                points=5,
                evidence=[context.changed_asset.urn],
            )

    @staticmethod
    def _classify(score: int) -> tuple[Severity, str]:
        if score >= 80:
            return Severity.CRITICAL, "block_and_remediate"
        if score >= 60:
            return Severity.HIGH, "generate_draft_pr"
        if score >= 30:
            return Severity.MEDIUM, "request_review"
        return Severity.LOW, "record_only"

    @staticmethod
    def _summary(
        event: ChangeEvent, context: ImpactContext, severity: Severity, score: int
    ) -> str:
        field = event.field or event.asset_name or event.asset_urn
        return (
            f"{severity.value.upper()} risk ({score}/100): {event.change_type.value} on {field} "
            f"affects {len(context.affected_features)} feature(s), "
            f"{len(context.affected_models)} model(s), and "
            f"{len(context.affected_deployments)} deployment(s)."
        )
