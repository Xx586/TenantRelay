# 开发者指南

## 本地后端

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
uvicorn api.main:app --reload
```

PostgreSQL、Redis 和 ChromaDB 可通过 Compose 单独启动。直接在宿主机运行时需要调整 `DATABASE_URL/REDIS_URL/CHROMA_HOST`。

## 本地前端

```bash
cd frontend
npm ci
npm run dev
```

Vite 会把 `/api` 代理到 `VITE_API_TARGET`，默认是 `http://localhost:8000`。

## 质量检查

```bash
cd backend && python -m pytest -q
ruff check backend
npm --prefix frontend test
npm --prefix frontend run build
```

代码提交前还应执行 `docker compose config --quiet` 并确认没有 `.env`、数据库文件或日志进入 Git。
