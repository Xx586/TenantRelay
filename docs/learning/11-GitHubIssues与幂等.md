# 11 GitHub Issues 与幂等

## 本章解决什么问题

理解为什么外部工单不能“失败就再创建一张”，以及 TenantRelay 如何用本地记录、GitHub Issues 和幂等键避免重复工单。

## 小白类比

网上付款超时时，不能立刻再付一次；要先记下订单号，再核对对方是否收到。GitHub 工单也一样。

## 前置知识

了解 HTTP POST、超时、HTTP 状态码和数据库唯一约束。

## 源码阅读顺序

`scenarios/saas/ticketing.py` → `SaaSStore.create_local_ticket` → `update_external_ticket` → `tests/test_saas_ticketing.py`。

## 核心类和函数解释

`TicketService.create()` 先用 `tenant_id + request_id` 创建本地记录，再根据 `TICKET_PROVIDER` 决定是否写 GitHub。`TicketCreateResult.uncertain` 专门表示“请求超时，对方可能已成功”。

## 一次真实输入如何流转

用户说“请创建工单”→ TicketAgent 生成交接摘要→ PostgreSQL 建立 `TR-...` 记录→ GitHub 返回 Issue 编号→本地工单保存 `external_id` 和链接。如果超时，状态变为 `unknown`，不再创建新工单。

## 可执行实验

运行 `pytest -q tests/test_saas_ticketing.py`，观察成功、401/403/429 和超时测试的状态变化。

## 常见错误

把 GitHub Token 写进 Prompt 或日志；超时后改用 PostgreSQL 再建一张工单；只在代码里“先查后写”却没有数据库唯一约束。

## 自测题及答案

问：为什么超时不等于失败？答：客户端没收到响应，不代表服务端没完成写入。

## 面试表达

“我用本地工单作为可追溯真相，用租户加请求 ID 做幂等，对外部写超时标记 UNKNOWN，避免非幂等降级导致重复工单。”
