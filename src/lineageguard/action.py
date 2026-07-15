from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from pydantic import BaseModel, Field

from lineageguard.models import ChangeEvent, ChangeType


class LineageGuardActionConfig(BaseModel):
    endpoint: str = "http://host.docker.internal:8000/api/v1/events"
    timeout_seconds: float = Field(default=30, gt=0, le=300)


def normalize_schema_mcl(event: Any) -> ChangeEvent | None:
    """Turn a DataHub schemaMetadata MCL into the small event contract we control."""
    mcl = event.event
    if getattr(mcl, "entityType", None) != "dataset":
        return None
    if getattr(mcl, "aspectName", None) != "schemaMetadata":
        return None

    current = _decode_generic_aspect(getattr(mcl, "aspect", None))
    previous = _decode_generic_aspect(getattr(mcl, "previousAspectValue", None))
    if not current or not previous:
        return None
    current_fields = _field_map(current)
    previous_fields = _field_map(previous)

    removed = sorted(set(previous_fields) - set(current_fields))
    added = sorted(set(current_fields) - set(previous_fields))
    changed = sorted(
        field
        for field in set(current_fields) & set(previous_fields)
        if _field_type(current_fields[field]) != _field_type(previous_fields[field])
    )

    change_type = ChangeType.UNKNOWN
    previous_field: str | None = None
    field: str | None = None
    old_type: str | None = None
    new_type: str | None = None
    if len(removed) == 1 and len(added) == 1:
        old, new = removed[0], added[0]
        if _field_type(previous_fields[old]) == _field_type(current_fields[new]):
            change_type = ChangeType.COLUMN_RENAMED
            previous_field, field = old, new
            old_type = _field_type(previous_fields[old])
            new_type = _field_type(current_fields[new])
    elif removed:
        change_type = ChangeType.COLUMN_REMOVED
        previous_field = removed[0]
        old_type = _field_type(previous_fields[removed[0]])
    elif changed:
        change_type = ChangeType.TYPE_CHANGED
        field = changed[0]
        old_type = _field_type(previous_fields[field])
        new_type = _field_type(current_fields[field])
    else:
        return None

    urn = str(getattr(mcl, "entityUrn", ""))
    fingerprint = json.dumps(
        [urn, change_type, previous_field, field, old_type, new_type],
        separators=(",", ":"),
    )
    event_id = "datahub-" + hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    return ChangeEvent(
        event_id=event_id,
        asset_urn=urn,
        asset_name=_dataset_name(urn),
        change_type=change_type,
        previous_field=previous_field,
        field=field,
        old_type=old_type,
        new_type=new_type,
        description="Detected from a DataHub schemaMetadata change log event.",
        metadata={"source": "datahub-actions", "event_type": event.event_type},
    )


def _decode_generic_aspect(aspect: Any) -> dict[str, Any]:
    if aspect is None:
        return {}
    value = getattr(aspect, "value", None)
    if not value:
        return {}
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _field_map(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["fieldPath"]): item
        for item in schema.get("fields", [])
        if isinstance(item, dict) and item.get("fieldPath")
    }


def _field_type(field: dict[str, Any]) -> str:
    native_type = field.get("nativeDataType")
    if native_type:
        return str(native_type)
    type_payload = field.get("type") or {}
    return json.dumps(type_payload, sort_keys=True, separators=(",", ":"))


def _dataset_name(urn: str) -> str | None:
    try:
        inner = urn.removeprefix("urn:li:dataset:(").removesuffix(")")
        qualified_name = inner.rsplit(",", 1)[0].split(",", 1)[1]
        return qualified_name.rsplit(".", 1)[-1]
    except (IndexError, ValueError):
        return None


def create_action_class() -> type:
    """Build the plugin class lazily so the core package works without Actions extras."""
    from datahub_actions.action.action import Action

    class LineageGuardDataHubAction(Action):
        @classmethod
        def create(cls, config_dict: dict, ctx: Any) -> LineageGuardDataHubAction:
            return cls(LineageGuardActionConfig.model_validate(config_dict or {}))

        def __init__(self, config: LineageGuardActionConfig) -> None:
            self.config = config
            self.client = httpx.Client(timeout=config.timeout_seconds)

        def act(self, event: Any) -> None:
            normalized = normalize_schema_mcl(event)
            if normalized is None:
                return
            response = self.client.post(
                self.config.endpoint,
                json=normalized.model_dump(mode="json"),
            )
            response.raise_for_status()

        def close(self) -> None:
            self.client.close()

    return LineageGuardDataHubAction


LineageGuardDataHubAction = create_action_class()
