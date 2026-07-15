# Security and safety model

- Secrets come only from environment variables and are never written to reports.
- DataHub mutation and GitHub publication are disabled by default.
- The DataHub MCP server runs in read-only mode; mutation tools are not enabled.
- Generated file paths must resolve inside the sandbox root.
- Each edit must have exactly one source match; ambiguous edits are rejected.
- Only an allowlisted `dbt build` subprocess runs, with a 180-second timeout.
- Validation happens in an OS temporary directory, not the working copy.
- GitHub publication uses exact file content updates and creates a draft PR.
- Docker Quickstart state is kept under the project `.runtime` home; cleanup and
  destructive Docker commands are deliberately absent.

For real production use, add workload identity, repository allowlists, signed event
verification, audit logging, network egress controls, and policy-specific approval
gates before enabling write paths.
