from lineageguard.context import StaticContextProvider
from lineageguard.models import ChangeEvent, ChangeType
from lineageguard.risk import RiskEngine


async def test_breaking_production_change_is_critical() -> None:
    event = ChangeEvent(
        event_id="test-1",
        asset_urn="urn:li:dataset:(urn:li:dataPlatform:duckdb,main.stg_customers,PROD)",
        change_type=ChangeType.COLUMN_RENAMED,
        previous_field="customer_age",
        field="age_years",
    )
    context = await StaticContextProvider().collect(event)
    report = RiskEngine().assess(event, context)

    assert report.score == 100
    assert report.severity.value == "critical"
    assert report.decision == "block_and_remediate"
    assert {signal.code for signal in report.signals} >= {
        "breaking_change",
        "ml_feature_impact",
        "production_impact",
    }
