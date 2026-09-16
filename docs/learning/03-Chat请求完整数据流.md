# 03 Chat 请求完整数据流

## 本章解决什么问题

跟踪一条“Python SDK 403，套餐刚降级”从 HTTP 进入到响应返回的全过程。

## 小白类比

一张快递单会经过验证、分拣、转运和签收；`request_id` 就是全程追踪号。

## 前置知识

完成前两章，了解 JSON 和 HTTP Header。

## 源码阅读顺序

`api/main.py::chat` → `MemoryManager.get_context` → `IntentRecognizer.recognize` → `_build_knowledge_context` → `SaaSAgentOrchestrator.run`。

## 核心类和函数解释

`ChatRequest` 负责输入校验，`_validated_tenant()` 负责认证，`_build_knowledge_context()` 负责 RAG 门控，`Request` 是传入编排器的内部数据包。

## 一次真实输入如何流转

1. Header 验证租户 API Key。
2. 脱敏 Token/Key。
3. 读取当前租户的记忆。
4. 识别 `sdk_error`，补充 `permission_request/subscription`。
5. 按租户和产品过滤 RAG。
6. Integration 与 Subscription 并行。
7. Composer 合并，回写记忆与 Trace。

## 可执行实验

调用 `/chat`，记录响应中的 `request_id`，再访问 `/trace/tool/{request_id}`。

## 常见错误

只看最终文字，不看 `primary_agent`、`supporting_agents`、`tools_used` 和 `knowledge_sources`，会错过系统的可解释性。

## 自测题及答案

问：为什么 RAG 放在 Agent 路由前？答：让所有被路由的 Agent 都获得同一份可核验事实。

## 面试表达

“我把主链路拆成可观测阶段，响应中显式返回路由理由、来源和工具记录。”
