from __future__ import annotations

from lineageguard.context import ContextProvider
from lineageguard.models import ChangeEvent, WorkflowResult
from lineageguard.repair import DeterministicRepairPlanner
from lineageguard.risk import RiskEngine


class LineageGuardWorkflow:
    def __init__(
        self,
        context_provider: ContextProvider,
        risk_engine: RiskEngine | None = None,
        repair_planner: DeterministicRepairPlanner | None = None,
    ) -> None:
        self.context_provider = context_provider
        self.risk_engine = risk_engine or RiskEngine()
        self.repair_planner = repair_planner or DeterministicRepairPlanner()

    async def run(self, event: ChangeEvent) -> WorkflowResult:
        context = await self.context_provider.collect(event)
        report = self.risk_engine.assess(event, context)
        repair_plan = self.repair_planner.plan(report)
        return WorkflowResult(report=report, repair_plan=repair_plan)
