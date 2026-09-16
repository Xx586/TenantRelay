# Docker 部署与排错

## 启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

启动顺序为 PostgreSQL/Redis/ChromaDB → Alembic Migration → Backend → Frontend/Prometheus。SaaSStore 会幂等写入演示租户和错误目录。

## 常用命令

```bash
docker compose logs -f backend
docker compose restart backend
docker compose down
docker compose down -v  # 会删除本地数据库和向量数据，仅在明确需要重置时使用
```

## 常见问题

- `401`：缺少租户头或 API Key。
- `403`：租户、API Key 不匹配，或请求的功能无权限。
- 后端无法启动：检查 `ANTHROPIC_API_KEY`、PostgreSQL 和 ChromaDB 健康状态。
- 端口被占用：修改 `.env` 中的 `APP_PORT/BACKEND_PORT/POSTGRES_PORT`。
- 首次镜像较慢：后端镜像会下载依赖和 ChromaDB 使用的嵌入模型缓存。
