# 10 PostgreSQL 与工单数据

## 本章解决什么问题

理解真实业务工具为什么需要关系数据库，以及工单如何持久化。

## 小白类比

模型的回答像口头答复，PostgreSQL 像正式登记册：记录存在才算真正创建。

## 前置知识

了解表、主键、外键、唯一约束和事务。

## 源码阅读顺序

`models.py` → `SaaSStore.initialize` → `seed_demo_data` → 租户/套餐查询 → `create_local_ticket` → Alembic migration。

## 核心类和函数解释

租户、订阅、功能开关、错误目录、服务白名单、工单、工单事件和工具审计分表存储。`tenant_id + request_id` 唯一约束保证幂等。

`Base` 统一模型元数据，`SaaSStore` 封装异步会话和所有带租户的查询，Alembic migration 记录可重放的表结构变更。

## 一次真实输入如何流转

租户认证用 API Key 哈希比对，套餐工具查询 `subscriptions` 和 `tenant_features`，工单创建在一个事务中写入 `support_tickets` 与 `ticket_events`。

## 可执行实验

创建工单后进入 PostgreSQL，查看 `support_tickets`、`ticket_events`、`tool_audit_logs` 三张表。

## 常见错误

先查再写仍可能有并发竞态，所以数据库还必须有唯一约束并捕获 `IntegrityError`。

## 自测题及答案

问：为什么 API Key 只存哈希？答：数据库泄露时不直接暴露原始 Key。

## 面试表达

“工单不是模型编造的文本，而是有唯一约束、事件记录和租户过滤的持久化业务对象。”
