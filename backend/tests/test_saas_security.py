import asyncio
import httpx
import pytest

from memory.conversation_memory import MemoryManager
from evaluation.saas_cases import SAAS_TOOL_FAILURE_CASES
from scenarios.saas.security import redact_sensitive_text
from scenarios.saas.tools import _safe_audit, _validate_health_url, check_service_statuses


class FakeTargetStore:
    async def service_targets(self, tenant_id, service_name=None):
        assert tenant_id == "tenant-a"
        return [{
            "service_name": service_name or "api",
            "region": "cn-east-1",
            "health_url": "https://status.example.test/health",
        }]


def test_sensitive_values_are_redacted_before_prompt_or_trace():
    raw = "Authorization Bearer abc.def.ghi api_key=super-secret password:letmein callback https://cb.test/hook?token=secret"
    safe = redact_sensitive_text(raw)
    assert "abc.def.ghi" not in safe
    assert "super-secret" not in safe
    assert "letmein" not in safe
    assert "token=secret" not in safe
    assert "https://cb.test/hook" not in safe
    assert "https://cb.test/<redacted-path>" in safe


def test_saas_profile_keeps_only_low_sensitivity_allowlist():
    profile = MemoryManager._sanitize_saas_profile({
        "sdk_languages": ["python"],
        "product_versions": ["v2"],
        "roles": ["开发者"],
        "preferences": ["中文"],
        "api_key": "must-not-survive",
        "webhook_url": "https://secret.example/hook",
    })
    assert profile == {
        "sdk_languages": ["python"],
        "product_versions": ["v2"],
        "roles": ["开发者"],
        "preferences": ["中文"],
    }


def test_nested_audit_payload_is_redacted():
    safe = _safe_audit({
        "result": {"token": "secret", "nested": ["api_key=another-secret"]},
        "description": "raw issue body",
    })
    assert safe["description"] == "<redacted>"
    assert safe["result"]["token"] == "<redacted>"
    assert "another-secret" not in safe["result"]["nested"][0]


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://169.254.169.254/latest/meta-data",
    "http://metadata.google.internal/computeMetadata/v1",
])
def test_health_check_rejects_invalid_or_metadata_urls(url):
    with pytest.raises(ValueError):
        _validate_health_url(url)


def test_service_status_uses_database_target_and_hides_url():
    def handler(request):
        assert str(request.url) == "https://status.example.test/health"
        return httpx.Response(200, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = asyncio.run(check_service_statuses(FakeTargetStore(), "tenant-a", "api", client))
    asyncio.run(client.aclose())
    assert result["services"][0]["healthy"] is True
    assert "health_url" not in result["services"][0]


@pytest.mark.parametrize("case", SAAS_TOOL_FAILURE_CASES)
def test_service_status_failure_dataset_is_handled_without_url_leak(case):
    failure = case["failure"]

    class CaseStore(FakeTargetStore):
        async def service_targets(self, tenant_id, service_name=None):
            targets = await super().service_targets(tenant_id, service_name)
            if failure == "partial":
                targets.append({
                    "service_name": "api-secondary", "region": "cn-east-2",
                    "health_url": "https://status.example.test/unhealthy",
                })
            return targets

    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if failure in {"dns", "circuit-open"}:
            raise httpx.ConnectError(failure, request=request)
        if failure == "connection-reset":
            raise httpx.RemoteProtocolError("reset", request=request)
        if failure == "partial" and request.url.path == "/unhealthy":
            return httpx.Response(500, request=request)
        status = {"500": 500, "403": 403, "429": 429}.get(failure, 200)
        return httpx.Response(status, request=request, content=b"not-json" if failure == "invalid-json" else b"")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = asyncio.run(check_service_statuses(CaseStore(), "tenant-a", "api", client))
    asyncio.run(client.aclose())
    assert len(result["services"]) == (2 if failure == "partial" else 1)
    assert "health_url" not in result["services"][0]
    if failure in {"500", "403", "429", "timeout", "dns", "circuit-open", "connection-reset"}:
        assert result["services"][0]["healthy"] is False
    if failure == "partial":
        assert [item["healthy"] for item in result["services"]] == [True, False]
