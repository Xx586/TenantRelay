"""SaaS Agent 可调用工具，统一做租户校验、审计和参数限制。"""

from __future__ import annotations

import time
from typing import Any, Dict
from urllib.parse import urlparse

import httpx

from agents.tools import AgentToolSpec, make_tool
from scenarios.saas.security import redact_sensitive_text
from scenarios.saas.store import SaaSStore
from scenarios.saas.ticketing import TicketService


async def check_service_statuses(
    store: SaaSStore,
    tenant_id: str,
    service_name: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """只检查数据库白名单中的目标，不接受用户传入 URL。"""
    targets = await store.service_targets(tenant_id, service_name)
    results = []
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=5.0, follow_redirects=False)
    try:
        for target in targets:
            _validate_health_url(target["health_url"])
            started = time.monotonic()
            try:
                response = await http_client.get(target["health_url"])
                results.append({
                    "service_name": target["service_name"],
                    "region": target["region"],
                    "healthy": response.is_success,
                    "status_code": response.status_code,
                    "latency_ms": round((time.monotonic() - started) * 1000, 1),
                })
            except httpx.HTTPError as ex:
                results.append({
                    "service_name": target["service_name"],
                    "region": target["region"],
                    "healthy": False,
                    "error": type(ex).__name__,
                })
    finally:
        if owns_client:
            await http_client.aclose()
    return {"services": results}


def build_saas_tools(store: SaaSStore, tickets: TicketService, rag_manager: Any) -> Dict[str, AgentToolSpec]:
    async def audited(req, name: str, action):
        try:
            data = await action()
            await store.audit(req.tenant_id, req.request_id, name, True, {"result": _safe_audit(data)})
            return {"success": True, **(data if isinstance(data, dict) else {"data": data})}
        except Exception as ex:
            safe_error = redact_sensitive_text(str(ex))[:200]
            await store.audit(req.tenant_id, req.request_id, name, False, {"error": safe_error})
            return {"success": False, "error": safe_error}

    async def search_product_docs(req, args):
        async def action():
            result = await rag_manager.search_with_rewrite(
                "knowledge_search", str(args.get("query") or req.message), int(args.get("top_k", 5)),
                filters={"tenant_id": req.tenant_id, "product": req.product,
                         "version": str(args.get("version") or "latest")},
            )
            if not result.success:
                raise RuntimeError(result.error or "产品文档检索失败")
            safe_results = []
            for item in result.data if isinstance(result.data, list) else []:
                if isinstance(item, dict):
                    item = dict(item)
                    for key in ("title", "content", "source"):
                        if key in item:
                            item[key] = redact_sensitive_text(str(item[key]))
                safe_results.append(item)
            return {"results": safe_results, "reranked": result.reranked}
        return await audited(req, "search_product_docs", action)

    async def lookup_api_error(req, args):
        return await audited(req, "lookup_api_error", lambda: store.lookup_error(
            req.tenant_id, str(args["error_code"]), str(args.get("api_path", "*")), req.product,
        ))

    async def lookup_tenant_config(req, args):
        return await audited(req, "lookup_tenant_config", lambda: store.tenant_summary(req.tenant_id))

    async def check_subscription(req, args):
        async def action():
            data = await store.subscription_summary(req.tenant_id)
            feature = str(args.get("feature") or "").strip()
            if data and feature:
                data["requested_feature"] = feature
                data["feature_enabled"] = bool(data["features"].get(feature, False))
            return data or {"found": False}
        return await audited(req, "check_subscription", action)

    async def get_service_status(req, args):
        service_name = str(args.get("service_name") or "") or None
        return await audited(
            req,
            "get_service_status",
            lambda: check_service_statuses(store, req.tenant_id, service_name),
        )

    async def create_support_ticket(req, args):
        explicit = any(word in req.message.lower() for word in ["创建工单", "提交工单", "转人工", "support ticket", "create ticket"])
        if not explicit:
            return {"success": False, "error": "用户未明确要求创建工单"}
        async def action():
            result = await tickets.create(req.tenant_id, req.request_id, str(args["title"]),
                                          str(args["description"]), str(args.get("priority", "medium")))
            return {**result.ticket, "created": result.created, "uncertain": result.uncertain}
        return await audited(req, "create_support_ticket", action)

    async def get_ticket_status(req, args):
        async def action():
            data = await tickets.get(req.tenant_id, str(args["ticket_id"]))
            return data or {"found": False}
        return await audited(req, "get_ticket_status", action)

    return {
        "search_product_docs": make_tool("search_product_docs", "按当前租户、产品和版本检索产品文档。", {"query": {"type": "string"}, "top_k": {"type": "integer"}, "version": {"type": "string"}}, search_product_docs, ["query"]),
        "lookup_api_error": make_tool("lookup_api_error", "查询真实错误码目录。", {"error_code": {"type": "string"}, "api_path": {"type": "string"}}, lookup_api_error, ["error_code"]),
        "get_service_status": make_tool("get_service_status", "检查白名单中的 SaaS 服务健康状态。", {"service_name": {"type": "string"}}, get_service_status),
        "lookup_tenant_config": make_tool("lookup_tenant_config", "只读查询当前租户配置摘要。", {}, lookup_tenant_config),
        "check_subscription": make_tool("check_subscription", "查询当前租户套餐、配额和功能权限。", {"feature": {"type": "string"}}, check_subscription),
        "create_support_ticket": make_tool("create_support_ticket", "在用户明确要求时创建幂等支持工单。", {"title": {"type": "string"}, "description": {"type": "string"}, "priority": {"type": "string"}}, create_support_ticket, ["title", "description"]),
        "get_ticket_status": make_tool("get_ticket_status", "查询当前租户的工单状态。", {"ticket_id": {"type": "string"}}, get_ticket_status, ["ticket_id"]),
    }


def _validate_health_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("非法健康检查 URL")
    # 目标 URL 必须来自数据库白名单；额外禁止常见元数据地址。
    if parsed.hostname in {"169.254.169.254", "metadata.google.internal"}:
        raise ValueError("禁止访问云元数据地址")


def _safe_audit(data: Any) -> Any:
    blocked = {"api_key", "token", "authorization", "description", "password", "secret"}
    if isinstance(data, dict):
        return {
            str(key): "<redacted>" if str(key).lower() in blocked else _safe_audit(value)
            for key, value in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [_safe_audit(value) for value in data[:50]]
    if isinstance(data, str):
        return redact_sensitive_text(data)[:500]
    if data is None or isinstance(data, (bool, int, float)):
        return data
    return redact_sensitive_text(str(data))[:500]
