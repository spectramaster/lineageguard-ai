# LineageGuard AI demo narration

This is LineageGuard AI: a DataHub-powered agent that stops silent data changes
before they break production machine-learning systems.

The incident in this demo looks small. A dbt model renames `customer_age` to
`age_years`. But a table-only view misses the real impact. DataHub holds the context
that makes the change operationally meaningful: the stable column contract, the
technical owner, Tier 1 and PII governance tags, and the downstream ML graph.

Here is that graph in a real local DataHub instance. The changed dbt dataset feeds the
`customer_age` ML feature, which is connected to a churn model and its production API
deployment. LineageGuard reads this context through the official DataHub MCP server,
with narrow SDK enrichment for the deployment relationship.

Now we run the same workflow from the LineageGuard interface. The agent normalizes
the schema event, traverses three hops of lineage, and applies a deterministic risk
policy. Every point is visible: thirty-five for a breaking rename, twenty-five for an
affected feature, twenty for a production deployment, and ten for sensitive data.

The result is a critical score of ninety out of one hundred, with a decision to block
and remediate. LineageGuard proposes the smallest compatibility repair: restore the
stable `customer_age` output alias. It applies that exact one-match patch only inside
a temporary project copy, then runs a real dbt build. All nine models and tests pass.
The working tree is never modified during validation.

The agent is deliberately bounded. MCP access is read-only. External mutation is off
by default. Ambiguous patches and path traversal are rejected. GitHub publication,
when enabled, can only create a draft pull request.

Finally, LineageGuard writes the decision back to DataHub as a durable document. The
next engineer or agent can see the impact, evidence, repair, validation result, owner,
and related dataset without reconstructing the incident from logs.

That closes the loop from context graph, to explainable decision, to minimal repair,
to executable proof, and back to reusable catalog context. LineageGuard AI is open
source, reproducible with zero credentials, and ready for the Production ML Agents
track of the Build with DataHub Agent Hackathon.
