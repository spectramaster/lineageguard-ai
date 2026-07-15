from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from datahub.emitter.mce_builder import make_data_platform_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata import schema_classes as models
from datahub.metadata.urns import (
    MlFeatureTableUrn,
    MlFeatureUrn,
    MlModelDeploymentUrn,
    MlModelGroupUrn,
    MlModelUrn,
)

from lineageguard.models import WorkflowResult


@dataclass(frozen=True)
class DemoMLGraph:
    source_dataset: str
    feature_table: str
    feature: str
    model_group: str
    model: str
    deployment: str


def demo_ml_graph() -> DemoMLGraph:
    platform = make_data_platform_urn("mlflow")
    return DemoMLGraph(
        source_dataset=(
            "urn:li:dataset:(urn:li:dataPlatform:dbt,"
            "lineageguard.main.stg_customers,PROD)"
        ),
        feature_table=str(MlFeatureTableUrn(platform, "customer_features")),
        feature=str(MlFeatureUrn("customer_features", "customer_age")),
        model_group=str(MlModelGroupUrn(platform, "customer-churn", "PROD")),
        model=str(MlModelUrn(platform, "churn-model-v3", "PROD")),
        deployment=str(
            MlModelDeploymentUrn(platform, "churn-api-production", "PROD")
        ),
    )


class DataHubGateway:
    """Small, auditable DataHub boundary for seed metadata and agent writeback."""

    def __init__(self, server: str, token: str | None = None) -> None:
        self.server = server.rstrip("/")
        self.token = token

    def test_connection(self) -> None:
        self._emitter().test_connection()

    def seed_demo_ml_graph(self) -> DemoMLGraph:
        graph = demo_ml_graph()
        platform_urn = make_data_platform_urn("mlflow")
        aspects: list[tuple[str, Any]] = [
            (
                platform_urn,
                models.DataPlatformInfoClass(
                    name="mlflow",
                    displayName="MLflow",
                    type=models.PlatformTypeClass.OTHERS,
                    datasetNameDelimiter=".",
                ),
            ),
            (
                "urn:li:tag:Tier1",
                models.TagPropertiesClass(
                    name="Tier1",
                    description="Business-critical production asset.",
                    colorHex="#E55353",
                ),
            ),
            (
                "urn:li:tag:PII",
                models.TagPropertiesClass(
                    name="PII",
                    description="Contains personally identifiable information.",
                    colorHex="#B83280",
                ),
            ),
            (
                "urn:li:corpuser:ml-platform",
                models.CorpUserInfoClass(
                    active=True,
                    displayName="ML Platform",
                    email="ml-platform@example.com",
                    title="ML Platform Team",
                ),
            ),
            (
                graph.source_dataset,
                models.GlobalTagsClass(
                    tags=[
                        models.TagAssociationClass(tag="urn:li:tag:Tier1"),
                        models.TagAssociationClass(tag="urn:li:tag:PII"),
                    ]
                ),
            ),
            (
                graph.source_dataset,
                self._technical_ownership(),
            ),
            (
                graph.feature,
                models.MLFeaturePropertiesClass(
                    description=(
                        "Customer age used by the production churn model. "
                        "Its source contract is stg_customers.customer_age."
                    ),
                    dataType=models.MLFeatureDataTypeClass.CONTINUOUS,
                    sources=[graph.source_dataset],
                    customProperties={"contractField": "customer_age"},
                ),
            ),
            (
                graph.feature_table,
                models.MLFeatureTablePropertiesClass(
                    description="Production customer features for churn inference.",
                    mlFeatures=[graph.feature],
                    mlPrimaryKeys=[],
                ),
            ),
            (
                graph.model_group,
                models.MLModelGroupPropertiesClass(
                    name="customer-churn",
                    description="Production customer churn model family.",
                ),
            ),
            (
                graph.deployment,
                models.MLModelDeploymentPropertiesClass(
                    description="Online churn scoring API.",
                    status=models.DeploymentStatusClass.IN_SERVICE,
                    customProperties={"environment": "production"},
                ),
            ),
            (
                graph.model,
                models.MLModelPropertiesClass(
                    name="churn-model-v3",
                    description="Current production churn classifier.",
                    type="classification",
                    mlFeatures=[graph.feature],
                    deployments=[graph.deployment],
                    groups=[graph.model_group],
                    customProperties={"stage": "Production"},
                ),
            ),
        ]
        governed_entities = [
            graph.feature,
            graph.feature_table,
            graph.model_group,
            graph.model,
            graph.deployment,
        ]
        aspects.extend((urn, self._technical_ownership()) for urn in governed_entities)
        aspects.extend(
            (
                urn,
                models.GlobalTagsClass(
                    tags=[models.TagAssociationClass(tag="urn:li:tag:Tier1")]
                ),
            )
            for urn in governed_entities
        )

        emitter = self._emitter()
        emitter.emit_mcps(
            [
                MetadataChangeProposalWrapper(entityUrn=urn, aspect=aspect)
                for urn, aspect in aspects
            ]
        )
        return graph

    def write_report_document(self, result: WorkflowResult) -> str:
        from datahub.sdk import DataHubClient
        from datahub.sdk.document import Document

        document_id = f"lineageguard-{result.report.event.event_id}"
        document = Document.create_document(
            id=document_id,
            title=(
                f"LineageGuard {result.report.severity.value.upper()}: "
                f"{result.report.event.asset_name or result.report.event.asset_urn}"
            ),
            subtype="LineageGuard Impact Report",
            text=self._report_markdown(result),
            related_assets=[result.report.event.asset_urn],
            owners=["urn:li:corpuser:ml-platform"],
            tags=["urn:li:tag:Tier1"],
            custom_properties={
                "riskScore": str(result.report.score),
                "decision": result.report.decision,
                "eventId": result.report.event.event_id,
            },
        )
        client = DataHubClient(server=self.server, token=self.token)
        client.entities.upsert(document)
        return str(document.urn)

    def _emitter(self) -> DatahubRestEmitter:
        return DatahubRestEmitter(self.server, token=self.token)

    @staticmethod
    def _technical_ownership() -> models.OwnershipClass:
        return models.OwnershipClass(
            owners=[
                models.OwnerClass(
                    owner="urn:li:corpuser:ml-platform",
                    type=models.OwnershipTypeClass.TECHNICAL_OWNER,
                )
            ]
        )

    @staticmethod
    def _report_markdown(result: WorkflowResult) -> str:
        signal_lines = "\n".join(
            f"- **{signal.label}:** +{signal.points} — {', '.join(signal.evidence)}"
            for signal in result.report.signals
        )
        repair = (
            f"## Proposed remediation\n\n"
            f"**{result.repair_plan.title}** — {result.repair_plan.explanation}"
            if result.repair_plan
            else "## Proposed remediation\n\nNo automated repair was proposed."
        )
        validation = (
            "passed" if result.validation and result.validation.passed else "not run"
        )
        event_json = json.dumps(
            result.report.event.model_dump(mode="json"), indent=2, ensure_ascii=False
        )
        return (
            f"# Impact summary\n\n{result.report.summary}\n\n"
            f"- Risk score: **{result.report.score}/100**\n"
            f"- Decision: **{result.report.decision}**\n"
            f"- Sandbox validation: **{validation}**\n\n"
            f"## Evidence\n\n{signal_lines}\n\n{repair}\n\n"
            f"## Normalized event\n\n```json\n{event_json}\n```\n"
        )
