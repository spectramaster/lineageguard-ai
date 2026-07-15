from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChangeType(StrEnum):
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_RENAMED = "column_renamed"
    TYPE_CHANGED = "type_changed"
    NULLABILITY_CHANGED = "nullability_changed"
    FRESHNESS_FAILED = "freshness_failed"
    PII_EXPOSURE = "pii_exposure"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntityRef(BaseModel):
    urn: str
    entity_type: str
    name: str | None = None
    platform: str | None = None
    tags: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class ChangeEvent(BaseModel):
    event_id: str
    asset_urn: str
    asset_name: str | None = None
    change_type: ChangeType
    field: str | None = None
    previous_field: str | None = None
    old_type: str | None = None
    new_type: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImpactContext(BaseModel):
    changed_asset: EntityRef
    downstream_entities: list[EntityRef] = Field(default_factory=list)
    affected_features: list[EntityRef] = Field(default_factory=list)
    affected_models: list[EntityRef] = Field(default_factory=list)
    affected_deployments: list[EntityRef] = Field(default_factory=list)
    governance_tags: list[str] = Field(default_factory=list)
    usage_score: float = Field(default=0, ge=0, le=1)


class RiskSignal(BaseModel):
    code: str
    label: str
    points: int = Field(ge=0)
    evidence: list[str] = Field(default_factory=list)


class ImpactReport(BaseModel):
    event: ChangeEvent
    severity: Severity
    score: int = Field(ge=0, le=100)
    decision: str
    summary: str
    signals: list[RiskSignal]
    context: ImpactContext
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FilePatch(BaseModel):
    path: str
    rationale: str
    original_text: str | None = None
    replacement_text: str | None = None


class RepairPlan(BaseModel):
    title: str
    strategy: str
    explanation: str
    patches: list[FilePatch] = Field(default_factory=list)
    requires_human_review: bool = True


class ValidationCheck(BaseModel):
    name: str
    command: list[str]
    passed: bool
    exit_code: int
    output: str = ""
    duration_seconds: float = 0


class ValidationResult(BaseModel):
    passed: bool
    checks: list[ValidationCheck] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    report: ImpactReport
    repair_plan: RepairPlan | None = None
    validation: ValidationResult | None = None
    pull_request_url: str | None = None
    writeback_urns: list[str] = Field(default_factory=list)
