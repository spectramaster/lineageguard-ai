---
name: ml-change-safety
description: Investigate a proposed or detected data change for downstream ML risk using DataHub context, then recommend a safely validated remediation.
---

# ML change safety

Use this skill when a dataset or schema change may affect features, models, or online
model deployments.

1. Fetch the changed entity and its schema, ownership, tags, and descriptions.
2. Traverse downstream lineage for at least three hops.
3. Explicitly identify MLFeature, MLModel, MLModelGroup, and deployment entities.
4. Separate observed DataHub facts from inferred risk.
5. Score breaking-change, production, governance, usage, and ownership evidence.
6. For critical risk, block the change and propose the smallest compatibility repair.
7. Apply code only in a temporary sandbox and run the project's real checks.
8. Create only a draft PR and require human review before merge.
9. Save the evidence, decision, patch rationale, and validation outcome back to DataHub.

Never claim validation passed unless the actual command exited successfully. Never
merge, deploy, delete metadata, or broaden a patch beyond the affected contract.
