from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from lineageguard.config import get_settings
from lineageguard.context import StaticContextProvider
from lineageguard.execution import RepairSandbox
from lineageguard.models import ChangeEvent, FilePatch
from lineageguard.workflow import LineageGuardWorkflow

app = typer.Typer(no_args_is_help=True)
demo_app = typer.Typer(no_args_is_help=True)
datahub_app = typer.Typer(no_args_is_help=True)
app.add_typer(demo_app, name="demo")
app.add_typer(datahub_app, name="datahub")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DBT_MODEL = PROJECT_ROOT / "demo/dbt_project/models/staging/stg_customers.sql"
FAULTS = PROJECT_ROOT / "demo/faults"


@app.command()
def analyze(event_file: Path) -> None:
    """Analyze a normalized change event without requiring DataHub credentials."""
    event = ChangeEvent.model_validate_json(event_file.read_text(encoding="utf-8"))
    result = asyncio.run(LineageGuardWorkflow(StaticContextProvider()).run(event))
    typer.echo(result.model_dump_json(indent=2))


@demo_app.command("inject")
def inject_fault(scenario: str = "breaking-schema") -> None:
    """Apply a deterministic dbt fault for the end-to-end demo."""
    scenario_file = FAULTS / f"{scenario}.sql"
    if not scenario_file.exists():
        raise typer.BadParameter(f"Unknown scenario: {scenario}")
    DBT_MODEL.write_text(scenario_file.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Injected {scenario} into {DBT_MODEL.relative_to(PROJECT_ROOT)}")


@demo_app.command()
def reset() -> None:
    """Restore the healthy dbt model."""
    healthy = FAULTS / "healthy.sql"
    DBT_MODEL.write_text(healthy.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo("Demo model reset to the healthy state.")


@demo_app.command()
def event() -> None:
    """Print the canonical breaking-change event used in the demo."""
    event_path = PROJECT_ROOT / "demo/events/breaking-column-rename.json"
    typer.echo(json.dumps(json.loads(event_path.read_text()), indent=2))


@demo_app.command()
def validate() -> None:
    """Validate the deterministic repair in a temporary sandbox."""
    event_path = PROJECT_ROOT / "demo/events/breaking-column-rename.json"
    change_event = ChangeEvent.model_validate_json(event_path.read_text(encoding="utf-8"))

    async def execute() -> dict[str, object]:
        result = await LineageGuardWorkflow(StaticContextProvider()).run(change_event)
        if not result.repair_plan:
            raise RuntimeError("No repair plan was produced")
        sandbox = RepairSandbox(PROJECT_ROOT, PROJECT_ROOT / ".venv/bin/dbt")
        preparation = FilePatch(
            path="demo/dbt_project/models/staging/stg_customers.sql",
            rationale="Reproduce the breaking rename only inside the validation sandbox.",
            original_text="as customer_age",
            replacement_text="as age_years",
        )
        validation_result, diff = await sandbox.validate(
            result.repair_plan, preparation_patches=[preparation]
        )
        result.validation = validation_result
        return {"result": result.model_dump(mode="json"), "diff": diff}

    typer.echo(json.dumps(asyncio.run(execute()), indent=2, default=str))


@datahub_app.command("test")
def datahub_test() -> None:
    """Verify the configured DataHub GMS connection."""
    from lineageguard.datahub import DataHubGateway

    settings = get_settings()
    DataHubGateway(settings.datahub_gms_url, settings.datahub_token).test_connection()
    typer.echo(f"Connected to DataHub at {settings.datahub_gms_url}")


@datahub_app.command("seed")
def datahub_seed() -> None:
    """Seed the demo ML feature, model, deployment, governance, and lineage context."""
    from lineageguard.datahub import DataHubGateway

    settings = get_settings()
    graph = DataHubGateway(
        settings.datahub_gms_url, settings.datahub_token
    ).seed_demo_ml_graph()
    typer.echo(json.dumps(graph.__dict__, indent=2))
