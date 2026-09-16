---
name: AcmeCloud API/SDK 集成支持规范
description: API、SDK、Webhook 和部署问题排查
keywords: API,SDK,Webhook,接口,回调,401,403,404,429,500,超时
agents: integration
enabled: true
---
# AcmeCloud API/SDK 集成支持规范

- 先收集 HTTP 方法、接口路径、错误码、request_id、SDK 语言/版本和环境。
- 401 优先检查认证，403 优先检查授权和套餐，429 检查限流与配额。
- 不要索要完整 API Key、Token、签名密钥或私钥。
- 每个排查步骤说明验证方式；不编造日志和服务状态。
