import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from evaluation.saas_cases import SAAS_TENANT_ISOLATION_CASES
from scenarios.saas.ticketing import TicketService


class FakeStore:
    def __init__(self):
        self.ticket = None
        self.saved_description = None

    async def create_local_ticket(self, tenant_id, request_id, title, description, priority, provider="postgres"):
        self.saved_description = description
        if self.ticket:
            return self.ticket, False
        self.ticket = {"ticket_id": "TR-TEST", "tenant_id": tenant_id, "request_id": request_id,
                       "title": title, "priority": priority, "status": "open", "provider": provider,
                       "external_id": None, "external_url": None}
        return self.ticket, True

    async def update_external_ticket(self, ticket_id, external_id, external_url, status):
        self.ticket.update(external_id=external_id, external_url=external_url, status=status)

    async def get_ticket(self, tenant_id, ticket_id):
        return self.ticket if self.ticket and self.ticket["tenant_id"] == tenant_id else None


def settings(provider="github"):
    return SimpleNamespace(ticket_provider=provider, github_token="secret-token", github_repository="owner/repo")


def test_github_ticket_success_and_idempotency():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer secret-token"
        return httpx.Response(201, json={"number": 42, "html_url": "https://github.test/42"})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store = FakeStore()
    service = TicketService(store, settings(), client)
    first = asyncio.run(service.create("tenant-a", "req-1", "SDK 403", "details"))
    second = asyncio.run(service.create("tenant-a", "req-1", "SDK 403", "details"))
    asyncio.run(client.aclose())
    assert first.ticket["external_id"] == "42"
    assert first.created is True
    assert second.created is False


def test_github_timeout_is_unknown_and_does_not_create_fallback():
    def handler(request):
        raise httpx.ReadTimeout("unknown write result", request=request)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store = FakeStore()
    service = TicketService(store, settings(), client)
    result = asyncio.run(service.create("tenant-a", "req-timeout", "Outage", "details", "critical"))
    asyncio.run(client.aclose())
    assert result.uncertain is True
    assert result.ticket["status"] == "unknown"
    assert result.ticket["ticket_id"] == "TR-TEST"


@pytest.mark.parametrize("status_code", [401, 403, 429])
def test_github_http_errors_are_persisted_without_fallback(status_code):
    def handler(request):
        return httpx.Response(status_code, request=request, json={"message": "provider rejected request"})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store = FakeStore()
    service = TicketService(store, settings(), client)
    result = asyncio.run(service.create("tenant-a", f"req-{status_code}", "SDK issue", "details"))
    asyncio.run(client.aclose())
    assert result.created is True
    assert result.uncertain is False
    assert result.ticket["status"] == f"provider_error_{status_code}"
    assert result.ticket["ticket_id"] == "TR-TEST"


@pytest.mark.parametrize("case", SAAS_TENANT_ISOLATION_CASES)
def test_ticket_lookup_is_tenant_scoped(case):
    store = FakeStore()
    service = TicketService(store, settings("postgres"))
    created = asyncio.run(service.create(case["owner"], case["resource"], "Title", "details"))
    assert asyncio.run(service.get(case["owner"], created.ticket["ticket_id"])) is not None
    assert asyncio.run(service.get(case["caller"], created.ticket["ticket_id"])) is None


def test_ticket_description_is_redacted_before_local_or_github_write():
    captured = {}
    def handler(request):
        captured.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(201, request=request, json={"number": 9, "html_url": "https://github.test/9"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store = FakeStore()
    service = TicketService(store, settings(), client)
    asyncio.run(service.create(
        "tenant-a", "req-secret", "API key problem",
        "api_key=super-secret callback https://hooks.example.com/full/path?token=secret",
    ))
    asyncio.run(client.aclose())
    assert "super-secret" not in store.saved_description
    assert "/full/path" not in store.saved_description
    assert "super-secret" not in captured["body"]
    assert "/full/path" not in captured["body"]
