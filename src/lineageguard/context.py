from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Protocol

from lineageguard.models import ChangeEvent, EntityRef, ImpactContext


class ContextProvider(Protocol):
    async def collect(self, event: ChangeEvent) -> ImpactContext: ...


class StaticContextProvider:
    """Deterministic context provider used by tests and the zero-credential demo."""

    async def collect(self, event: ChangeEvent) -> ImpactContext:
        dataset = EntityRef(
            urn=event.asset_urn,
            entity_type="dataset",
            name=event.asset_name or "stg_customers",
            platform="dbt",
            tags=["Tier1", "PII"],
            owners=["urn:li:corpuser:ml-platform"],
        )
        feature = EntityRef(
            urn="urn:li:mlFeature:(customer_features,customer_age)",
            entity_type="mlFeature",
            name="customer_age",
        )
        model = EntityRef(
            urn="urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn-model-v3,PROD)",
            entity_type="mlModel",
            name="churn-model-v3",
        )
        deployment = EntityRef(
            urn=(
                "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,"
                "churn-api-production,PROD)"
            ),
            entity_type="mlModelDeployment",
            name="churn-api-production",
            properties={"status": "IN_SERVICE"},
        )
        return ImpactContext(
            changed_asset=dataset,
            downstream_entities=[feature, model, deployment],
            affected_features=[feature],
            affected_models=[model],
            affected_deployments=[deployment],
            governance_tags=["PII", "Tier1"],
            usage_score=0.91,
        )


class DataHubMCPContextProvider:
    """Collects authoritative context through DataHub's official MCP endpoint."""

    def __init__(
        self,
        url: str,
        token: str | None = None,
        max_hops: int = 3,
        gms_url: str | None = None,
    ) -> None:
        self.url = url
        self.token = token
        self.max_hops = max_hops
        self.gms_url = gms_url

    async def collect(self, event: ChangeEvent) -> ImpactContext:
        from fastmcp import Client

        client = Client(self._transport(), auth=self.token if not self._is_stdio else None)
        async with client:
            entity_result = await client.call_tool(
                "get_entities", {"urns": [event.asset_urn]}
            )
            lineage_result = await client.call_tool(
                "get_lineage",
                {
                    "urn": event.asset_urn,
                    "upstream": False,
                    "max_hops": self.max_hops,
                    "max_results": 100,
                },
            )
            lineage_payload = self._decode_result(lineage_result)
            lineage_entities = self._extract_entities(lineage_payload)
            related_result = None
            if lineage_entities:
                related_result = await client.call_tool(
                    "get_entities", {"urns": [entity.urn for entity in lineage_entities]}
                )

        entity_payload = self._decode_result(entity_result)
        related_payload = self._decode_result(related_result) if related_result else {}
        entities_by_urn = {
            entity.urn: entity
            for entity in [
                *lineage_entities,
                *self._extract_entities(related_payload),
            ]
        }
        entities = list(entities_by_urn.values())
        changed_candidates = self._extract_entities(entity_payload)
        changed = changed_candidates[0] if changed_candidates else EntityRef(
            urn=event.asset_urn,
            entity_type="dataset",
            name=event.asset_name,
        )

        features = [e for e in entities if e.entity_type.lower() == "mlfeature"]
        models = [e for e in entities if e.entity_type.lower() == "mlmodel"]
        deployments = [
            e for e in entities if e.entity_type.lower() == "mlmodeldeployment"
        ]
        if not deployments and models:
            deployments = self._sdk_deployments(models)
            entities.extend(deployments)
        governance_tags = sorted({*changed.tags, *(tag for e in entities for tag in e.tags)})
        return ImpactContext(
            changed_asset=changed,
            downstream_entities=entities,
            affected_features=features,
            affected_models=models,
            affected_deployments=deployments,
            governance_tags=governance_tags,
            usage_score=self._usage_score(changed),
        )

    @property
    def _is_stdio(self) -> bool:
        return self.url.startswith("stdio://")

    def _transport(self) -> Any:
        if not self._is_stdio:
            return self.url
        from fastmcp.client.transports import StdioTransport

        command = self.url.removeprefix("stdio://")
        executable = shutil.which(command)
        if not executable:
            venv_candidate = Path(sys.executable).parent / command
            executable = str(venv_candidate) if venv_candidate.is_file() else None
        if not executable:
            raise RuntimeError(f"MCP command not found: {command}")
        environment = dict(os.environ)
        if self.gms_url:
            environment["DATAHUB_GMS_URL"] = self.gms_url
        if self.token:
            environment["DATAHUB_GMS_TOKEN"] = self.token
        return StdioTransport(
            command=executable,
            args=[],
            env=environment,
            log_file=Path(os.devnull),
        )

    def _sdk_deployments(self, models: list[EntityRef]) -> list[EntityRef]:
        if not self.gms_url:
            return []
        from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph
        from datahub.metadata.schema_classes import (
            MLModelDeploymentPropertiesClass,
            MLModelPropertiesClass,
        )

        graph = DataHubGraph(
            DatahubClientConfig(server=self.gms_url, token=self.token)
        )
        deployment_urns: set[str] = set()
        for model in models:
            properties = graph.get_aspect(model.urn, MLModelPropertiesClass)
            if properties and properties.deployments:
                deployment_urns.update(properties.deployments)
        deployments: list[EntityRef] = []
        for urn in sorted(deployment_urns):
            properties = graph.get_aspect(urn, MLModelDeploymentPropertiesClass)
            deployments.append(
                EntityRef(
                    urn=urn,
                    entity_type="mlModelDeployment",
                    name=urn.rsplit(",", 2)[-2] if "," in urn else urn,
                    properties=properties.to_obj() if properties else {},
                )
            )
        return deployments

    @staticmethod
    def _decode_result(result: Any) -> Any:
        data = getattr(result, "data", None)
        if data is not None:
            return data
        blocks = getattr(result, "content", [])
        texts = [
            getattr(block, "text", "")
            for block in blocks
            if getattr(block, "text", "")
        ]
        if not texts:
            return {}
        combined = "\n".join(texts)
        try:
            return json.loads(combined)
        except json.JSONDecodeError:
            return {"text": combined}

    @classmethod
    def _extract_entities(cls, payload: Any) -> list[EntityRef]:
        records: dict[str, EntityRef] = {}
        entity_urn_types = {
            "container",
            "dataset",
            "dataFlow",
            "dataJob",
            "mlFeature",
            "mlFeatureTable",
            "mlModel",
            "mlModelDeployment",
            "mlModelGroup",
        }

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                urn = value.get("urn") or value.get("entityUrn")
                if isinstance(urn, str) and urn.startswith("urn:li:"):
                    urn_type = urn.split(":", 3)[2]
                    declared_type = value.get("type") or value.get("entityType")
                    if urn_type in entity_urn_types or declared_type in entity_urn_types:
                        ref = cls._entity_ref(value, urn)
                        records.setdefault(urn, ref)
                for key, nested in value.items():
                    if key in {"deployments", "groups", "mlFeatures", "sources"}:
                        for related_urn in nested if isinstance(nested, list) else []:
                            if isinstance(related_urn, str) and related_urn.startswith(
                                "urn:li:"
                            ):
                                records.setdefault(
                                    related_urn,
                                    cls._entity_ref({"urn": related_urn}, related_urn),
                                )
                    visit(nested)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(payload)
        return list(records.values())

    @staticmethod
    def _entity_ref(value: dict[str, Any], urn: str) -> EntityRef:
        entity_type = value.get("type") or value.get("entityType")
        if not entity_type:
            entity_type = urn.split(":", 3)[2]
        tags_raw = value.get("tags") or []
        if isinstance(tags_raw, dict):
            tags_raw = tags_raw.get("tags") or []
        tags: list[str] = []
        if isinstance(tags_raw, list):
            for tag in tags_raw:
                if isinstance(tag, str):
                    tags.append(tag.rsplit(":", 1)[-1])
                elif isinstance(tag, dict):
                    nested_tag = tag.get("tag") if isinstance(tag.get("tag"), dict) else {}
                    tag_value = (
                        tag.get("name")
                        or tag.get("urn")
                        or nested_tag.get("urn")
                        or nested_tag.get("properties", {}).get("name")
                    )
                    if tag_value:
                        tags.append(str(tag_value).rsplit(":", 1)[-1])
        owners_raw = value.get("owners") or value.get("ownership") or []
        if isinstance(owners_raw, dict):
            owners_raw = owners_raw.get("owners") or []
        owners = (
            [
                str(
                    owner.get("urn")
                    or (
                        owner.get("owner", {}).get("urn")
                        if isinstance(owner.get("owner"), dict)
                        else None
                    )
                    or owner
                )
                if isinstance(owner, dict)
                else str(owner)
                for owner in owners_raw
            ]
            if isinstance(owners_raw, list)
            else []
        )
        platform_raw = value.get("platform")
        platform = (
            platform_raw.get("name") or platform_raw.get("urn")
            if isinstance(platform_raw, dict)
            else platform_raw
        )
        return EntityRef(
            urn=urn,
            entity_type=str(entity_type),
            name=value.get("name") or value.get("displayName"),
            platform=platform,
            tags=tags,
            owners=owners,
            properties=value,
        )

    @staticmethod
    def _usage_score(entity: EntityRef) -> float:
        raw = entity.properties.get("usageScore", entity.properties.get("usage_score", 0))
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0
        return max(0, min(value, 1))
