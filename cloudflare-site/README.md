# Cloudflare judge experience

This directory contains the static, zero-secret judge experience deployed on
Cloudflare's free tier. It is deliberately an **evidence replay**, not a claim that the
full DataHub stack runs at the edge.

The UI replays the verified result in `artifacts/sample-live-result.json` and presents
the captured DataHub screenshots already preserved in `assets/`.

Verification before deployment:

```bash
python -m http.server 4173 --directory cloudflare-site
curl -fsS http://127.0.0.1:4173/ >/dev/null
```

The deployment must not contain credentials, local runtime files, or generated claims.
