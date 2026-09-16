# 14 Docker 部署、接口演示与排错

## 本章解决什么问题

把 FastAPI、Redis、ChromaDB 和 PostgreSQL 组成可重复启动的本地环境，并完成一次 SaaS 演示。

## 小白类比

Docker Compose 像一张套餐清单：一条命令同时准备应用、缓存、知识库和业务数据库。

## 前置知识

了解镜像、容器、端口、环境变量和健康检查。

## 源码阅读顺序

`.env.example` → `docker-compose.yml` → `backend/Dockerfile` → `backend/api/main.py` 的 lifespan → `backend/alembic/versions/0001_saas_schema.py`。

## 核心类和函数解释

`lifespan()` 按场景初始化组件；`SaaSSettings.from_env()` 集中解析配置；Compose 中的 `depends_on.condition` 等待 PostgreSQL 和 Redis 健康后再启动应用。

## 一次真实输入如何流转

容器启动→创建表并写入 `demo-tenant`→请求 `/chat` 携带租户头→查错误目录和 basic 套餐→返回 Integration 主 Agent 与 Subscription 辅 Agent→再请求创建工单并查询。

## 可执行实验

```bash
cp .env.example .env
# 填写 ANTHROPIC_API_KEY，然后启动
docker compose up --build
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: demo-tenant' \
  -H 'X-API-Key: demo-secret-change-me' \
  -d '{"message":"Python SDK 返回 403，刚降级到 basic 套餐","user_id":"u1","conv_id":"c1","product":"AcmeCloud","environment":"production"}'
```

## 常见错误

在主机与容器中都用 `localhost` 访问其他容器；忘记设置 SaaS 场景；把真实 Token 提交到 `.env.example`。

## 自测题及答案

问：为什么容器内的 PostgreSQL 主机名是 `postgres`？答：Compose 会为服务名提供内部 DNS，`localhost` 只指向当前容器。

## 面试表达

“项目用 Compose 编排 FastAPI、Redis、ChromaDB 和 PostgreSQL 16，依赖健康检查后启动，并提供演示租户和可复现的接口链路。”
