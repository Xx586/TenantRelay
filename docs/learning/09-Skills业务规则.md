# 09 Skills 业务规则

## 本章解决什么问题

理解 Skills 和 RAG 的分工：一个管“应该怎么做”，一个管“事实是什么”。

## 小白类比

知识库是产品手册，Skill 是员工行为规范。

## 前置知识

会读 Markdown 和顶部 front matter。

## 源码阅读顺序

`Skill` → `matches` → `SkillManager.load` → `prompt_for` → `BaseAgent._build_system_prompt`。

## 核心类和函数解释

SaaS 模式加载客户成功、集成、订阅、故障、工单五套规则。`agents` 限制角色，`keywords` 决定是否命中，`/skills/reload` 运行时重载。

## 一次真实输入如何流转

IntegrationAgent 接到 Webhook 问题时，`SkillManager.prompt_for()` 按 Agent 和关键词选中集成 Skill，将诊断 SOP 注入系统 Prompt，业务事实仍由工具查询。

## 可执行实验

修改集成 Skill 中的一条回答规则，调用 `/skills/reload`，再用 `/skills` 确认加载路径。

## 常见错误

把可变业务事实硬编进 Skill，导致套餐变更后回答过期。可变事实应由工具或 RAG 提供。

## 自测题及答案

问：修改 Agent Python 类后能否只调 reload 生效？答：不能，reload 只重读 Skill 文件，Python 代码仍需重启。

## 面试表达

“把处理 SOP 从代码中抽离为按角色和关键词注入的热加载 Skill。”
