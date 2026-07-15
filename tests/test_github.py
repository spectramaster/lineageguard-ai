import base64

import httpx

from lineageguard.github import GitHubDraftPRPublisher
from lineageguard.models import ChangeEvent, ChangeType, FilePatch, RepairPlan


def test_github_publisher_creates_scoped_draft_pr() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/repos/acme/features" and request.method == "GET":
            return httpx.Response(200, json={"default_branch": "main"})
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "base-sha"}})
        if path.endswith("/git/refs"):
            return httpx.Response(201, json={"ref": "created"})
        if "/contents/" in path and request.method == "GET":
            content = "select 2026 - birth_year as age_years\n"
            return httpx.Response(
                200,
                json={
                    "sha": "file-sha",
                    "content": base64.b64encode(content.encode()).decode(),
                },
            )
        if "/contents/" in path and request.method == "PUT":
            return httpx.Response(200, json={"content": {"sha": "updated"}})
        if path.endswith("/pulls"):
            body = request.read().decode()
            assert '"draft":true' in body
            return httpx.Response(201, json={"html_url": "https://github.com/acme/features/pull/7"})
        raise AssertionError(f"Unexpected request: {request.method} {path}")

    publisher = GitHubDraftPRPublisher(
        "secret",
        "acme/features",
        api_url="https://api.github.test",
        client=httpx.Client(
            base_url="https://api.github.test", transport=httpx.MockTransport(handler)
        ),
    )
    event = ChangeEvent(
        event_id="rename-001",
        asset_urn="urn:li:dataset:(urn:li:dataPlatform:duckdb,main.stg_customers,PROD)",
        change_type=ChangeType.COLUMN_RENAMED,
        previous_field="customer_age",
        field="age_years",
    )
    plan = RepairPlan(
        title="Preserve customer_age",
        strategy="compatibility_alias",
        explanation="Restore the stable feature contract.",
        patches=[
            FilePatch(
                path="models/stg_customers.sql",
                rationale="Production feature compatibility.",
                original_text="as age_years",
                replacement_text="as customer_age",
            )
        ],
    )

    url = publisher.publish(plan, event)

    assert url == "https://github.com/acme/features/pull/7"
    assert [request.method for request in requests] == ["GET", "GET", "POST", "GET", "PUT", "POST"]
