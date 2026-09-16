"""PostgreSQL / GitHub Issues 工单适配。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from scenarios.saas.config import SaaSSettings
from scenarios.saas.security import redact_sensitive_text
from scenarios.saas.store import SaaSStore


@dataclass
class TicketCreateResult:
    ticket: dict
    created: bool
    uncertain: bool = False


class TicketService:
    def __init__(self, store: SaaSStore, settings: SaaSSettings, client: Optional[httpx.AsyncClient] = None):
        self.store = store
        self.settings = settings
        self._client = client

    async def create(self, tenant_id: str, request_id: str, title: str,
                     description: str, priority: str = "medium") -> TicketCreateResult:
        provider = self.settings.ticket_provider
        title = redact_sensitive_text(title)
        description = redact_sensitive_text(description)
        local, created = await self.store.create_local_ticket(
            tenant_id, request_id, title, description, priority, provider=provider,
        )
        if not created or provider == "postgres":
            return TicketCreateResult(local, created)

        if not self.settings.github_token or not self.settings.github_repository:
            await self.store.update_external_ticket(local["ticket_id"], None, None, "provider_config_error")
            local = await self.store.get_ticket(tenant_id, local["ticket_id"]) or local
            return TicketCreateResult(local, True)

        payload = {
            "title": f"[{priority.upper()}] {title}"[:256],
            "body": f"TenantRelay ticket: {local['ticket_id']}\nTenant: {tenant_id}\nRequest: {request_id}\n\n{description}",
            "labels": ["tenantrelay", f"priority:{priority}"],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = f"https://api.github.com/repos/{self.settings.github_repository}/issues"
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            await self.store.update_external_ticket(local["ticket_id"], str(data.get("number")), data.get("html_url"), "open")
            local = await self.store.get_ticket(tenant_id, local["ticket_id"]) or local
            return TicketCreateResult(local, True)
        except (httpx.TimeoutException, httpx.TransportError):
            # 写请求可能已在 GitHub 成功；标记未知，不创建第二张工单。
            await self.store.update_external_ticket(local["ticket_id"], None, None, "unknown")
            local = await self.store.get_ticket(tenant_id, local["ticket_id"]) or local
            return TicketCreateResult(local, True, uncertain=True)
        except httpx.HTTPStatusError as ex:
            await self.store.update_external_ticket(local["ticket_id"], None, None, f"provider_error_{ex.response.status_code}")
            local = await self.store.get_ticket(tenant_id, local["ticket_id"]) or local
            return TicketCreateResult(local, True)
        finally:
            if owns_client:
                await client.aclose()

    async def get(self, tenant_id: str, ticket_id: str) -> Optional[dict]:
        return await self.store.get_ticket(tenant_id, ticket_id)
