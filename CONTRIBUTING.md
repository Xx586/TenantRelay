# Contributing

感谢你改进 TenantRelay。

1. 从 `main` 创建功能分支。
2. 不要提交 `.env`、Token、真实租户数据、数据库文件或日志。
3. 新业务规则优先放入对应 Skill 或 `scenarios/saas/`，避免破坏基础客服场景。
4. 新工具必须验证 `tenant_id`，外部 URL 必须来自白名单。
5. 工单写操作必须保持幂等，并且只能由明确用户操作触发。
6. 提交前运行后端测试、前端测试/构建和 Compose 配置检查。

Pull Request 请说明问题、方案、测试证据和安全影响。不要填写未实际执行得到的性能指标。
