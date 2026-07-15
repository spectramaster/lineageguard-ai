# Five-minute demo script

1. Open DataHub at `http://localhost:9002` and show the dbt `stg_customers` asset with
   PII, Tier1, owner, schema, and downstream lineage to the ML feature and model.
2. Open LineageGuard at `http://localhost:8000` and click **Analyze and validate**.
3. Explain the evidence-backed score: breaking contract, ML feature, production
   deployment, and PII governance.
4. Show the exact rollback patch and the passing nine-step dbt build in the isolated
   sandbox.
5. Open the newly created DataHub decision document. Emphasize that the next engineer
   or agent receives the impact analysis and remediation rationale as catalog context.
6. Optional: enable GitHub publishing and show the draft PR. Do not merge it in the
   demo.

## Live Actions variant

Run the API and `datahub-actions` pipeline, then emit a schemaMetadata rename. The
Action normalizes the MCL and invokes the same workflow automatically. Restore the
healthy schema after the demonstration.

## What not to claim

- The demo does not deploy a production model.
- The GitHub publisher creates a draft, never an automatic merge.
- OSS DataHub does not expose usage percentiles in this demo, so the real MCP score is
  90 rather than the zero-credential fixture's 100.
