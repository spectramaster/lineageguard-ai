import json
from types import SimpleNamespace

from datahub.metadata.schema_classes import GenericAspectClass

from lineageguard.action import normalize_schema_mcl
from lineageguard.models import ChangeType


def _aspect(field_name: str) -> GenericAspectClass:
    payload = {
        "fields": [
            {
                "fieldPath": field_name,
                "nativeDataType": "INTEGER",
                "type": {"type": {"com.linkedin.schema.NumberType": {}}},
            }
        ]
    }
    return GenericAspectClass(
        value=json.dumps(payload).encode(), contentType="application/json"
    )


def test_schema_mcl_rename_is_normalized() -> None:
    envelope = SimpleNamespace(
        event_type="MetadataChangeLogEvent_v1",
        event=SimpleNamespace(
            entityType="dataset",
            entityUrn=(
                "urn:li:dataset:(urn:li:dataPlatform:dbt,"
                "lineageguard.main.stg_customers,PROD)"
            ),
            aspectName="schemaMetadata",
            previousAspectValue=_aspect("customer_age"),
            aspect=_aspect("age_years"),
        ),
    )

    event = normalize_schema_mcl(envelope)

    assert event is not None
    assert event.change_type == ChangeType.COLUMN_RENAMED
    assert event.previous_field == "customer_age"
    assert event.field == "age_years"
    assert event.asset_name == "stg_customers"
