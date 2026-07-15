from lineageguard.context import StaticContextProvider
from lineageguard.models import ChangeEvent, ChangeType
from lineageguard.workflow import LineageGuardWorkflow


async def test_workflow_produces_compatibility_repair() -> None:
    event = ChangeEvent(
        event_id="test-2",
        asset_urn="urn:li:dataset:(urn:li:dataPlatform:duckdb,main.stg_customers,PROD)",
        change_type=ChangeType.COLUMN_RENAMED,
        previous_field="customer_age",
        field="age_years",
    )
    result = await LineageGuardWorkflow(StaticContextProvider()).run(event)

    assert result.repair_plan is not None
    assert result.repair_plan.strategy == "compatibility_alias"
    assert result.repair_plan.patches[0].original_text == "as age_years"
    assert result.repair_plan.patches[0].replacement_text == "as customer_age"
