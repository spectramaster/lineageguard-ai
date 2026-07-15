from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from lineageguard.config import get_settings
from lineageguard.context import DataHubMCPContextProvider, StaticContextProvider
from lineageguard.execution import RepairSandbox
from lineageguard.models import ChangeEvent, FilePatch, WorkflowResult
from lineageguard.workflow import LineageGuardWorkflow

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
context_provider = (
    DataHubMCPContextProvider(
        settings.datahub_mcp_url,
        settings.datahub_token,
        gms_url=settings.datahub_gms_url,
    )
    if settings.context_mode == "mcp"
    else StaticContextProvider()
)
workflow = LineageGuardWorkflow(context_provider)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/api/v1/events", response_model=WorkflowResult)
async def analyze_event(event: ChangeEvent) -> WorkflowResult:
    return await workflow.run(event)


@app.post("/api/v1/demo/validate", response_model=WorkflowResult)
async def validate_demo(event: ChangeEvent) -> WorkflowResult:
    result = await workflow.run(event)
    if result.repair_plan and result.repair_plan.patches:
        project_root = Path(__file__).resolve().parents[2]
        sandbox = RepairSandbox(project_root, project_root / ".venv/bin/dbt")
        preparation = FilePatch(
            path="demo/dbt_project/models/staging/stg_customers.sql",
            rationale="Reproduce the breaking rename only inside the validation sandbox.",
            original_text="as customer_age",
            replacement_text="as age_years",
        )
        validation, _ = await sandbox.validate(
            result.repair_plan, preparation_patches=[preparation]
        )
        result.validation = validation
        if (
            validation.passed
            and settings.enable_github_pr
            and settings.github_token
            and settings.github_repository
        ):
            from lineageguard.github import GitHubDraftPRPublisher

            result.pull_request_url = GitHubDraftPRPublisher(
                settings.github_token, settings.github_repository
            ).publish(result.repair_plan, result.report.event)
        if validation.passed and settings.enable_datahub_writeback:
            from lineageguard.datahub import DataHubGateway

            document_urn = DataHubGateway(
                settings.datahub_gms_url, settings.datahub_token
            ).write_report_document(result)
            result.writeback_urns.append(document_urn)
    return result


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = Path(__file__).parent / "web" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
