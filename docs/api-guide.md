# API 使用指南

Swagger 在服务启动后位于 `http://localhost:8000/docs`，通过前端网关访问时为 `http://localhost/api/docs`。

## SaaS 认证

SaaS 模式的受保护接口需要：

```http
X-Tenant-ID: demo-tenant
X-API-Key: demo-key-change-me
```

API Key 只保存 SHA-256 哈希。不要把真实 Token、API Key 或完整回调 URL放入对话或工单。

## 主要接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/chat` | 主对话链路 |
| POST | `/search` | 租户感知知识检索 |
| POST | `/knowledge/add` | 添加结构化文档 |
| POST | `/knowledge/upload` | 上传 Markdown/TXT/JSON |
| GET | `/monitor` | 运行指标摘要 |
| GET | `/trace/tool/{request_id}` | 工具调用 Trace |
| POST | `/eval/run` | 运行内置评测 |
| GET | `/saas/tenants/current` | 当前租户摘要 |
| GET | `/saas/subscription` | 套餐、配额与权限 |
| GET | `/saas/services/status` | 白名单服务状态 |
| POST | `/saas/tickets` | 显式创建工单 |
| GET | `/saas/tickets/{ticket_id}` | 查询租户工单 |

可执行请求见 [examples/api-requests.http](../examples/api-requests.http)。
