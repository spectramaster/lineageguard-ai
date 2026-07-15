from __future__ import annotations

import base64
import hashlib
import re

import httpx

from lineageguard.models import ChangeEvent, RepairPlan


class GitHubPublishError(RuntimeError):
    pass


class GitHubDraftPRPublisher:
    """Publishes an exact, already-validated patch without mutating the local checkout."""

    def __init__(
        self,
        token: str,
        repository: str,
        api_url: str = "https://api.github.com",
        client: httpx.Client | None = None,
    ) -> None:
        if repository.count("/") != 1:
            raise ValueError("repository must use the owner/name form")
        self.repository = repository
        self.api_url = api_url.rstrip("/")
        self.client = client or httpx.Client(
            base_url=self.api_url,
            timeout=30,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def publish(
        self,
        plan: RepairPlan,
        event: ChangeEvent,
        base_branch: str | None = None,
    ) -> str:
        if not plan.patches:
            raise GitHubPublishError("repair plan has no file patches")

        repository = self._request("GET", f"/repos/{self.repository}")
        base = base_branch or repository["default_branch"]
        base_ref = self._request(
            "GET", f"/repos/{self.repository}/git/ref/heads/{base}"
        )
        branch = self._branch_name(event)
        self._request(
            "POST",
            f"/repos/{self.repository}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_ref["object"]["sha"]},
        )

        for patch in plan.patches:
            content = self._request(
                "GET",
                f"/repos/{self.repository}/contents/{patch.path}",
                params={"ref": branch},
            )
            if patch.original_text is None or patch.replacement_text is None:
                raise GitHubPublishError("GitHub patches require exact old and new text")
            current = base64.b64decode(content["content"]).decode("utf-8")
            occurrences = current.count(patch.original_text)
            if occurrences != 1:
                raise GitHubPublishError(
                    f"Expected one match in {patch.path}; found {occurrences}"
                )
            updated = current.replace(patch.original_text, patch.replacement_text, 1)
            self._request(
                "PUT",
                f"/repos/{self.repository}/contents/{patch.path}",
                json={
                    "message": f"LineageGuard: {plan.title}",
                    "content": base64.b64encode(updated.encode()).decode(),
                    "sha": content["sha"],
                    "branch": branch,
                },
            )

        pull_request = self._request(
            "POST",
            f"/repos/{self.repository}/pulls",
            json={
                "title": f"[LineageGuard] {plan.title}",
                "head": branch,
                "base": base,
                "draft": True,
                "body": self._pull_request_body(plan, event),
            },
        )
        return str(pull_request["html_url"])

    def _request(self, method: str, path: str, **kwargs: object) -> dict:
        response = self.client.request(method, path, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubPublishError(
                f"GitHub {method} {path} failed with {response.status_code}"
            ) from exc
        payload = response.json()
        if not isinstance(payload, dict):
            raise GitHubPublishError(f"GitHub {method} {path} returned a non-object")
        return payload

    @staticmethod
    def _branch_name(event: ChangeEvent) -> str:
        slug = re.sub(r"[^a-zA-Z0-9-]+", "-", event.event_id).strip("-").lower()
        digest = hashlib.sha256(event.asset_urn.encode()).hexdigest()[:8]
        return f"lineageguard/{slug[:40]}-{digest}"

    @staticmethod
    def _pull_request_body(plan: RepairPlan, event: ChangeEvent) -> str:
        patch_list = "\n".join(f"- `{patch.path}` — {patch.rationale}" for patch in plan.patches)
        return (
            "## Why this PR exists\n\n"
            f"LineageGuard detected `{event.change_type.value}` on "
            f"`{event.asset_urn}`.\n\n"
            f"{plan.explanation}\n\n"
            "## Validated changes\n\n"
            f"{patch_list}\n\n"
            "The patch was applied and tested in an isolated dbt sandbox before this "
            "draft PR was created. Human approval is still required before merge.\n"
        )
