# Submission evidence ledger

Verified in the authenticated Devpost interface on 2026-07-16.

## Final state

- Competition: Build with DataHub — The Agent Hackathon
- Project: LineageGuard AI
- Devpost status: `Submitted`
- Submission ID: `1085773`
- Public project page: <https://devpost.com/software/lineageguard-ai>
- Public source repository: <https://github.com/spectramaster/lineageguard-ai>
- Public demo video: <https://www.youtube.com/watch?v=NZnraMjL0iA>
- Public judge experience: <https://lineageguard-ai.pages.dev/>
- Track: Production ML Agents

The public page visibly contains the complete story, DataHub technology explanation,
verified result summary, source link, cover media, playable YouTube video, built-with
tags, and competition attribution.

## Cloudflare production verification

The permanent Pages hostname was deployed from the committed `cloudflare-site/`
source and verified on 2026-07-16:

- `https://lineageguard-ai.pages.dev/` returns HTTP 200;
- the returned HTML is byte-identical to `cloudflare-site/index.html` by SHA-256;
- all three DataHub evidence screenshots and the project cover return HTTP 200 with
  the expected media types;
- CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
  `Permissions-Policy` response headers are present;
- Chrome completed all five replay stages, displayed the final result cards, and
  recorded no console errors.

The page states that it is a captured evidence replay backed by a real DataHub OSS
1.6.0 and official MCP 0.6.0 run. It does not imply that the complete DataHub stack is
hosted by Cloudflare.

## Verified public claims

- real DataHub OSS graph and official MCP context;
- dataset → feature → model → production deployment impact;
- explainable `90/100` critical decision;
- isolated repair validation passing all nine dbt nodes/tests;
- durable DataHub decision-document writeback;
- ten automated tests and five deterministic evaluation cases;
- public Apache-2.0 repository and successful GitHub Actions CI.

## Creator contribution

The public project member record states:

> I designed and implemented the end-to-end agent: DataHub MCP and Actions integration,
> deterministic risk policy, sandboxed dbt repair validation, DataHub decision writeback,
> tests, demo, and documentation.

## Preservation rule

Do not replace the video, source URL, or verified numeric claims unless the replacement
has been tested publicly. Reopen the Devpost editor only for a specific, evidence-backed
improvement and reconfirm `Submitted` afterward.
