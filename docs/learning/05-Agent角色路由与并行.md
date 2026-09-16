# 05 Agent 角色、路由与并行

## 本章解决什么问题

理解五个 Agent 为什么需要分工，以及复合问题如何主辅协作。

## 小白类比

医院分诊不会让所有科室都回答；路由先选主责，再在真正跨领域时请会诊。

## 前置知识

完成意图识别章，了解继承和类属性。

## 源码阅读顺序

`AgentProfile` → SaaS 五个 Agent → `_domain_scores` → `_collaboration_targets` → `run_parallel` → `ResponseComposer`。

## 核心类和函数解释

- Profile 规定职责、输入/输出契约、升级条件和工具范围。
- 领域得分融合意图、关键词、实体和 Monitor 惩罚。
- `asyncio.gather()` 并行执行主辅 Agent。
- Composer 去重、处理冲突，不能补造业务事实。

## 一次真实输入如何流转

SDK 403 且提到套餐降级时，Integration 获得最高领域分，Subscription 因辅意图参与；两者并行查询后由 Composer 合并。

## 可执行实验

运行 `pytest tests/test_saas_scenario.py -k composite -q`，观察 Integration 为主、Subscription 为辅。

## 常见错误

为了“看起来是 Multi-Agent”而每次同时调五个 Agent，会增加成本、延迟和冲突。

## 自测题及答案

问：Monitor 惩罚在 SaaS 路由中改变什么？答：它直接降低领域得分，不再只用于同类实例排序。

## 面试表达

“多 Agent 的差异落在契约、工具权限和路由上，而不只是换一段 Prompt。”
