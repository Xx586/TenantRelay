# 12 Monitor、Trace、熔断与降级

## 本章解决什么问题

理解 Agent 出错、变慢或工具不可用时，系统如何可观测并保持可用。

## 小白类比

Trace 是快递物流，Monitor 是仓库大屏，熔断器是跳闸开关，fallback 是临时备用方案。

## 前置知识

了解耗时、成功率、异常捕获和状态机。

## 源码阅读顺序

`monitor/performance_monitor.py` → `agents/agent_orchestrator.py` 中的 Trace → `mcp/tool_manager.py` 的重试/熔断/降级 → `/monitor`。

## 核心类和函数解释

`PerformanceMonitor` 聚合 Agent 指标；`ExecutionTrace` 保留路由和工具步骤；`CircuitBreaker` 在连续失败后暂停请求；`MCPToolManager` 统一执行超时、重试和 fallback。

## 一次真实输入如何流转

SDK 403 请求进入编排器→ Trace 记录意图、主辅 Agent 和工具→错误目录查询超时→工具管理器重试/降级→ Monitor 记录失败与延迟→后续路由降低不稳定 Agent 的得分。

## 可执行实验

暂停 ChromaDB 后请求 `/chat`，再查看 `/monitor` 和响应的 `trace`，确认主流程仍能返回降级答复。

## 常见错误

在 Trace 中保存 API Key；把所有异常都吞掉；只统计平均延迟而忽略高分位延迟。

## 自测题及答案

问：熔断和重试的区别？答：重试对当次失败再尝试；熔断在故障持续时暂停新调用，防止级联失败。

## 面试表达

“编排层会记录脱敏 Trace，Monitor 的实时惩罚分参与路由，工具层提供超时、熔断和可观测降级。”
