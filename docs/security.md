# 安全设计

## 已实现

- 租户和 API Key 双字段认证，数据库只保存 API Key 哈希。
- 数据查询必须携带经过验证的 `tenant_id`。
- RAG、Redis 记忆和工单按租户隔离。
- Token、API Key 和完整回调 URL 在进入上下文前脱敏。
- 服务状态只能访问数据库白名单目标，防止任意 URL 请求。
- 工单要求用户显式触发，并使用幂等键。
- GitHub Token 不进入 Prompt、Trace、日志或 API 响应。
- CORS 来源通过环境变量配置，不默认开放全部来源。

## 生产环境仍需补充

- 使用企业身份系统、短期凭证和密钥轮换代替演示 API Key。
- 在网关层配置 TLS、限流、WAF 和审计留存周期。
- 限制 Swagger、Prometheus、数据库和缓存的公网访问。
- 使用云密钥管理服务注入 LLM 和 GitHub Token。
- 对上传文件增加恶意内容扫描和更严格的类型验证。

发现安全问题时，请阅读根目录 [SECURITY.md](../SECURITY.md)，不要在公开 Issue 中提交密钥或漏洞利用细节。
