from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from lineageguard.context import StaticContextProvider
from lineageguard.models import ChangeEvent
from lineageguard.workflow import LineageGuardWorkflow

ROOT = Path(__file__).resolve().parents[1]
ASSET_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:dbt,"
    "lineageguard.main.stg_customers,PROD)"
)


async def evaluate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    workflow = LineageGuardWorkflow(StaticContextProvider())
    outcomes: list[dict[str, Any]] = []
    for case in cases:
        event_payload = {
            key: value
            for key, value in case.items()
            if key
            not in {
                "id",
                "expected_score",
                "expected_severity",
                "expected_decision",
            }
        }
        event = ChangeEvent(
            event_id=f"eval-{case['id']}",
            asset_urn=ASSET_URN,
            asset_name="stg_customers",
            **event_payload,
        )
        result = await workflow.run(event)
        actual = {
            "score": result.report.score,
            "severity": result.report.severity.value,
            "decision": result.report.decision,
        }
        expected = {
            "score": case["expected_score"],
            "severity": case["expected_severity"],
            "decision": case["expected_decision"],
        }
        outcomes.append(
            {
                "id": case["id"],
                "passed": actual == expected,
                "expected": expected,
                "actual": actual,
            }
        )
    passed = sum(outcome["passed"] for outcome in outcomes)
    return {
        "summary": {
            "passed": passed,
            "total": len(outcomes),
            "accuracy": passed / len(outcomes) if outcomes else 0,
        },
        "cases": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads((ROOT / "evals/cases.json").read_text(encoding="utf-8"))
    report = asyncio.run(evaluate(cases))
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if report["summary"]["passed"] != report["summary"]["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
