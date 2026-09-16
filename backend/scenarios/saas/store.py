"""SaaS 场景的异步 PostgreSQL 仓库与演示数据。"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from scenarios.saas.models import (
    ApiErrorCatalog, Base, ServiceTarget, Subscription, SupportTicket,
    Tenant, TenantFeature, TicketEvent, ToolAuditLog,
)


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SaaSStore:
    def __init__(self, database_url: str):
        self.engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialize(self, demo_tenant_id: str, demo_api_key: str) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.seed_demo_data(demo_tenant_id, demo_api_key)

    async def close(self) -> None:
        await self.engine.dispose()

    async def seed_demo_data(self, tenant_id: str, api_key: str) -> None:
        async with self.sessions() as session:
            if await session.get(Tenant, tenant_id) is None:
                session.add(Tenant(
                    id=tenant_id, name="AcmeCloud Demo Corp", api_key_hash=hash_api_key(api_key),
                    region="cn-east-1", config={"sso": False, "webhook": True, "data_residency": "CN"},
                ))
                session.add(Subscription(
                    tenant_id=tenant_id, plan_name="basic", api_quota=10000,
                    expires_at=datetime.utcnow() + timedelta(days=180),
                ))
                session.add_all([
                    TenantFeature(tenant_id=tenant_id, feature_name="api_access", enabled=True),
                    TenantFeature(tenant_id=tenant_id, feature_name="batch_upload", enabled=False),
                    TenantFeature(tenant_id=tenant_id, feature_name="sso", enabled=False),
                    TenantFeature(tenant_id=tenant_id, feature_name="webhook", enabled=True),
                ])
            existing_error = await session.scalar(select(ApiErrorCatalog.id).limit(1))
            if existing_error is None:
                session.add_all([
                    ApiErrorCatalog(error_code="401", api_path="*", meaning="认证失败", common_causes=["Token 过期", "API Key 错误", "签名时间戳偏差"], next_steps=["刷新 Token", "核对环境和 Key", "检查签名时间戳"]),
                    ApiErrorCatalog(error_code="403", api_path="*", meaning="已认证但无资源权限", common_causes=["套餐不包含功能", "租户功能未开启", "IP 白名单限制"], next_steps=["查询套餐权限", "检查租户功能开关", "核对 IP 白名单"]),
                    ApiErrorCatalog(error_code="429", api_path="*", meaning="请求超过限额", common_causes=["超过每分钟限流", "超过套餐配额"], next_steps=["指数退避重试", "查询套餐配额"]),
                    ApiErrorCatalog(error_code="500", api_path="*", meaning="服务端处理异常", common_causes=["依赖服务异常", "参数触发未处理分支"], next_steps=["保留 request_id", "查询服务状态", "持续发生时创建工单"], requires_escalation=True),
                ])
            existing_target = await session.scalar(select(ServiceTarget.id).limit(1))
            if existing_target is None:
                session.add_all([
                    ServiceTarget(tenant_id="public", service_name="knowledge", region="cn-east-1",
                                  health_url="http://chromadb:8000/api/v1/heartbeat"),
                    ServiceTarget(tenant_id="public", service_name="tenantrelay-api", region="cn-east-1",
                                  health_url="http://127.0.0.1:8000/health"),
                ])
            await session.commit()

    async def authenticate(self, tenant_id: str, api_key: str) -> bool:
        async with self.sessions() as session:
            tenant = await session.get(Tenant, tenant_id)
            return bool(
                tenant and tenant.status == "active"
                and hmac.compare_digest(tenant.api_key_hash, hash_api_key(api_key))
            )

    async def tenant_summary(self, tenant_id: str) -> Optional[dict]:
        async with self.sessions() as session:
            tenant = await session.get(Tenant, tenant_id)
            if tenant is None:
                return None
            features = (await session.scalars(select(TenantFeature).where(TenantFeature.tenant_id == tenant_id))).all()
            return {"tenant_id": tenant.id, "name": tenant.name, "region": tenant.region, "status": tenant.status,
                    "config": tenant.config, "features": {row.feature_name: row.enabled for row in features}}

    async def subscription_summary(self, tenant_id: str) -> Optional[dict]:
        async with self.sessions() as session:
            row = await session.get(Subscription, tenant_id)
            if row is None:
                return None
            features = (await session.scalars(select(TenantFeature).where(TenantFeature.tenant_id == tenant_id))).all()
            return {"tenant_id": tenant_id, "plan_name": row.plan_name, "status": row.status,
                    "expires_at": row.expires_at.isoformat() if row.expires_at else None, "api_quota": row.api_quota,
                    "features": {item.feature_name: item.enabled for item in features}}

    async def lookup_error(
        self,
        tenant_id: str,
        code: str,
        api_path: str = "*",
        product: str = "AcmeCloud",
    ) -> Optional[dict]:
        async with self.sessions() as session:
            tenant = await session.get(Tenant, tenant_id)
            if tenant is None or tenant.status != "active":
                return None
            stmt = select(ApiErrorCatalog).where(
                ApiErrorCatalog.error_code == code,
                ApiErrorCatalog.product == product,
                or_(ApiErrorCatalog.api_path == api_path, ApiErrorCatalog.api_path == "*"),
            ).order_by((ApiErrorCatalog.api_path == api_path).desc())
            row = await session.scalar(stmt)
            if row is None:
                return None
            return {"error_code": row.error_code, "api_path": row.api_path, "meaning": row.meaning,
                    "common_causes": row.common_causes, "next_steps": row.next_steps,
                    "requires_escalation": row.requires_escalation}

    async def service_targets(self, tenant_id: str, service_name: Optional[str] = None) -> list[dict]:
        async with self.sessions() as session:
            stmt = select(ServiceTarget).where(
                ServiceTarget.enabled.is_(True),
                ServiceTarget.tenant_id.in_(["public", tenant_id]),
            )
            if service_name:
                stmt = stmt.where(ServiceTarget.service_name == service_name)
            rows = (await session.scalars(stmt)).all()
            return [{"service_name": r.service_name, "region": r.region, "health_url": r.health_url} for r in rows]

    async def create_local_ticket(self, tenant_id: str, request_id: str, title: str,
                                  description: str, priority: str, provider: str = "postgres") -> tuple[dict, bool]:
        async with self.sessions() as session:
            existing = await session.scalar(select(SupportTicket).where(
                SupportTicket.tenant_id == tenant_id, SupportTicket.request_id == request_id,
            ))
            if existing:
                return self._ticket_dict(existing), False
            ticket = SupportTicket(
                id=f"TR-{uuid.uuid4().hex[:10].upper()}", tenant_id=tenant_id, request_id=request_id,
                title=title[:200], description=description, priority=priority, provider=provider,
                status="provider_pending" if provider == "github" else "open",
            )
            session.add(ticket)
            session.add(TicketEvent(ticket_id=ticket.id, event_type="created", detail={"provider": provider}))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await session.scalar(select(SupportTicket).where(
                    SupportTicket.tenant_id == tenant_id, SupportTicket.request_id == request_id,
                ))
                if existing:
                    return self._ticket_dict(existing), False
                raise
            return self._ticket_dict(ticket), True

    async def update_external_ticket(self, ticket_id: str, external_id: Optional[str], external_url: Optional[str], status: str) -> None:
        async with self.sessions() as session:
            ticket = await session.get(SupportTicket, ticket_id)
            if ticket:
                ticket.external_id, ticket.external_url, ticket.status = external_id, external_url, status
                session.add(TicketEvent(ticket_id=ticket_id, event_type="provider_update", detail={"external_id": external_id, "status": status}))
                await session.commit()

    async def get_ticket(self, tenant_id: str, ticket_id: str) -> Optional[dict]:
        async with self.sessions() as session:
            row = await session.scalar(select(SupportTicket).where(
                SupportTicket.id == ticket_id, SupportTicket.tenant_id == tenant_id,
            ))
            return self._ticket_dict(row) if row else None

    async def audit(self, tenant_id: str, request_id: str, tool_name: str, success: bool, detail: dict) -> None:
        async with self.sessions() as session:
            session.add(ToolAuditLog(tenant_id=tenant_id, request_id=request_id, tool_name=tool_name,
                                     success=success, detail=detail))
            await session.commit()

    @staticmethod
    def _ticket_dict(row: SupportTicket) -> dict:
        return {"ticket_id": row.id, "tenant_id": row.tenant_id, "request_id": row.request_id,
                "title": row.title, "priority": row.priority, "status": row.status,
                "provider": row.provider, "external_id": row.external_id, "external_url": row.external_url,
                "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}
