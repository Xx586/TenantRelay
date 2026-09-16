# 02 Python 与 FastAPI 必备基础

## 本章解决什么问题

看懂项目中的 `async/await`、dataclass、Enum、Pydantic 和 FastAPI 装饰器。

## 小白类比

`async` 像客服把“等数据库”的号码放一边，先处理别的客户；`await` 是等该结果真正需要时再取。

## 前置知识

变量、函数、类、列表和字典。

## 源码阅读顺序

先看 `ChatRequest/ChatResponse`，再看 `chat()`，最后看 `lifespan()` 如何创建全局组件。

## 核心类和函数解释

- Pydantic 检查 API JSON 字段。
- Enum 限制意图和 Agent 只能取已知值。
- dataclass 是内部流转的轻量数据包。
- `asyncio.gather()` 并行等待多个 Agent 或检索。
- FastAPI `@app.post` 把函数变成 HTTP 接口。

## 一次真实输入如何流转

JSON 请求先被 `ChatRequest` 验证，FastAPI 将其传给异步 `chat()`，`await` 数据库和 Agent 结果，最后将 `ChatResponse` 序列化为 JSON。

## 可执行实验

启动后访问 `/docs`，展开 `/chat`，对照 `ChatRequest` 看 Swagger 如何生成字段。

## 常见错误

在异步函数中忘记 `await`，得到的会是 coroutine 对象而不是数据。

## 自测题及答案

问：为什么 ChromaDB 同步调用要放进 `asyncio.to_thread()`？答：避免阻塞 FastAPI 事件循环。

## 面试表达

“主链路使用 async I/O，对同步向量库调用做线程池隔离。”
