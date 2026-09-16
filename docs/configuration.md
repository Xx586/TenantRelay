# 配置说明

配置从根目录 `.env` 读取。请从 `.env.example` 创建，不要提交真实 `.env`。

| 变量 | 说明 | 默认值 |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM 密钥 | 无 |
| `ANTHROPIC_MODEL` | 模型名称 | 示例值 |
| `ANTHROPIC_BASE_URL` | 可选兼容端点 | 空 |
| `TENANTRELAY_SCENARIO` | `saas` 或 `customer_support` | `saas` |
| `SAAS_DEMO_TENANT_ID` | 本地演示租户 | `demo-tenant` |
| `SAAS_DEMO_API_KEY` | 本地演示 Key | `demo-key-change-me` |
| `SAAS_AUTH_ENABLED` | 是否启用租户认证 | `true` |
| `SAAS_DEFAULT_PRODUCT` | 演示产品 | `AcmeCloud` |
| `TICKET_PROVIDER` | `postgres` 或 `github` | `postgres` |
| `GITHUB_REPOSITORY` | GitHub 工单仓库 `owner/repo` | 空 |
| `GITHUB_TOKEN` | GitHub Token | 空 |
| `CORS_ORIGINS` | 允许的前端来源，逗号分隔 | 本地地址 |

生产环境必须替换数据库密码、Redis 密码、演示 API Key，并通过密钥管理服务注入外部 Token。
