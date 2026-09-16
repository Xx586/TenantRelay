# 07 RAG 切片、过滤与来源

## 本章解决什么问题

理解为什么要先找文档再回答，以及 SaaS 中版本和租户过滤的重要性。

## 小白类比

闭卷考试靠记忆，RAG 像允许带一本指定版本的手册并标注页码。

## 前置知识

了解 Embedding 把文本变成向量，相近文本的向量更接近。

## 源码阅读顺序

`KnowledgeBase.add_documents` → `search` → `MCPToolManager.search_with_rewrite` → API `_build_knowledge_context`。

## 核心类和函数解释

文档切成约 500 字片段，元数据包含租户、产品、版本、类型和来源。查询先改写再并行召回、去重、重排，最终把 Top-K 和来源交给 Agent。

## 一次真实输入如何流转

功能咨询通过 RAG 门控后，查询被改写，ChromaDB 只检索 `public` 或当前租户且产品/版本匹配的片段，返回内容与来源。

## 可执行实验

先用 `/knowledge/add` 导入一篇带 `version=v2` 的文档，再分别指定 `v2` 和 `latest` 调用 `/search`。

## 常见错误

只做向量检索不做租户过滤，可能把 A 企业私有文档召回给 B 企业。

## 自测题及答案

问：为什么响应要返回 `knowledge_sources`？答：让用户和评测器核验答案依据。

## 面试表达

“RAG 不是无差别搜索，而是意图门控加租户/产品/版本过滤。”
