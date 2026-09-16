"""PostgreSQL 集成测试。设置 SAAS_TEST_DATABASE_URL 后执行，默认不触碰开发数据库。"""

import os
import uuid

import pytest

from scenarios.saas.store import SaaSStore


@pytest.mark.asyncio
async def test_postgres_tenant_subscription_and_ticket_crud():
    database_url = os.getenv("SAAS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set SAAS_TEST_DATABASE_URL to run PostgreSQL integration test")

    tenant_id = f"test-{uuid.uuid4().hex[:10]}"
    store = SaaSStore(database_url)
    try:
        await store.initialize(tenant_id, "test-api-key")
        assert await store.authenticate(tenant_id, "test-api-key") is True
        assert await store.authenticate(tenant_id, "wrong") is False
        assert (await store.subscription_summary(tenant_id))["plan_name"] == "basic"

        first, created = await store.create_local_ticket(tenant_id, "req-1", "SDK 403", "details", "high")
        duplicate, created_again = await store.create_local_ticket(tenant_id, "req-1", "SDK 403", "details", "high")
        assert created is True
        assert created_again is False
        assert duplicate["ticket_id"] == first["ticket_id"]
        assert await store.get_ticket("another-tenant", first["ticket_id"]) is None
    finally:
        await store.close()
