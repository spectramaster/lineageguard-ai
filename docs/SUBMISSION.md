# Hackathon submission draft

## Project name

LineageGuard AI

## Challenge

Production ML Agents

## One-line pitch

An event-driven DataHub agent that stops silent data-contract changes before they
break production ML, proves a repair in a sandbox, and preserves the decision as
reusable catalog context.

## Problem

Schema changes that look small at the table level can invalidate features, models,
online deployments, and governance obligations. Existing impact tools often stop at a
lineage list; responders still have to interpret severity, author a fix, prove it, and
leave durable context for the next incident.

## Solution

LineageGuard consumes DataHub schema events, queries the official MCP server for
multi-hop context, calculates an explainable risk score, proposes a constrained repair,
runs dbt validation in a temporary copy, optionally opens a GitHub draft PR, and writes
the outcome back as a DataHub document.

## What is technically distinctive

- Crosses dbt datasets, MLFeature, MLModel, and MLModelDeployment rather than stopping
  at table lineage.
- Couples agent reasoning to an explicit risk policy and hard safety gates.
- Converts remediation into tested evidence, not prose-only advice.
- Closes the context loop by writing a durable incident decision back to DataHub.
- Includes both zero-credential reproducibility and a real DataHub/MCP/Actions path.

## Verified demo result

- Real MCP impact: 1 feature, 1 model, 1 production deployment, PII, Tier1, and owner.
- Risk: 90/100, critical, block and remediate.
- Repair: roll back `age_years` to the stable `customer_age` output contract.
- Validation: dbt build passes all 9 nodes/tests in an isolated sandbox.
- Real-time Action writeback:
  `urn:li:document:lineageguard-datahub-31e4e1b6a72c9344`.
- Packaging: a fresh locked Docker image passes `/health`, the complete validation
  API, and the browser-driven demo with no frontend console errors.

## Open-source use

The implementation uses Apache-2.0 DataHub projects and standard libraries. The SSPL
dbt Impact Action was studied only to avoid duplicating its product scope; no source was
copied. See `NOTICE`.

## Future work

Policy packs per domain, richer column-level repairs, model-specific smoke tests,
approval workflows, DataHub Cloud usage signals, and repository-scale multi-file PRs.
