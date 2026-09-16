"""SaaS 场景配置：所有密钥只在这一层读取，不进入 Prompt。"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class SaaSSettings:
    database_url: str
    demo_tenant_id: str
    demo_api_key: str
    auth_enabled: bool
    ticket_provider: str
    github_token: str
    github_repository: str
    product: str

    @classmethod
    def from_env(cls) -> "SaaSSettings":
        provider = os.getenv("TICKET_PROVIDER", "postgres").strip().lower()
        if provider not in {"postgres", "github"}:
            raise ValueError("TICKET_PROVIDER 只能是 postgres 或 github")
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://tenantrelay:tenantrelay@postgres:5432/tenantrelay",
            ),
            demo_tenant_id=os.getenv("SAAS_DEMO_TENANT_ID", "demo-tenant"),
            demo_api_key=os.getenv("SAAS_DEMO_API_KEY", "demo-key-change-me"),
            auth_enabled=os.getenv("SAAS_AUTH_ENABLED", "true").lower() not in {"0", "false", "no"},
            ticket_provider=provider,
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_repository=os.getenv("GITHUB_REPOSITORY", ""),
            product=os.getenv("SAAS_DEFAULT_PRODUCT", "AcmeCloud"),
        )
