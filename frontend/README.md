# TenantRelay Frontend

基于 Vue 3 + Vite 的 SaaS 支持工作台，只连接 TenantRelay Python API。

```bash
npm ci
npm run dev
npm test
npm run build
```

默认 API 前缀为 `/api`，开发代理目标可通过 `VITE_API_TARGET` 修改。API Key 只存入当前浏览会话的 `sessionStorage`，不会写入持久化设置。
