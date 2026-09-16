---
name: AcmeCloud 工单交接规范
description: 真实工单创建、幂等和敏感信息边界
keywords: 创建工单,提交工单,转人工,工单进度,ticket,support ticket
agents: ticket
enabled: true
---
# AcmeCloud 工单交接规范

- 只有用户明确要求时才能创建工单。
- 工单必须携带租户、request_id、摘要、环境和优先级。
- 依赖幂等键避免重复创建；只返回工具生成的工单号。
- 移除 Token、API Key、密码和完整支付凭证等敏感信息。
