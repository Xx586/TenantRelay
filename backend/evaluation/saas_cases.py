"""SaaS 场景可重现的基础评测集（10 类意图 x 15 条）。"""

from evaluation.evaluator import IntentTestCase


_SEEDS = {
    "feature_inquiry": ["是否支持 SSO", "有批量导入功能吗", "介绍一下审计日志功能"],
    "onboarding": ["新用户怎么开始", "如何创建第一个租户", "帮我完成首次接入"],
    "api_integration": ["上传 API 怎么调", "POST /v1/files 参数是什么", "API 签名如何实现"],
    "sdk_error": ["Python SDK 运行报错", "Java SDK 无法上传", "SDK 3.2.1 返回异常"],
    "webhook_failure": ["Webhook 回调失败", "回调验签不通过", "Webhook 一直超时"],
    "permission_request": ["为什么返回 403", "帮我开通导出权限", "账号没有 API 权限"],
    "tenant_configuration": ["查看租户配置", "企业租户怎么配置 SSO", "我们的数据区域是什么"],
    "incident_report": ["生产服务挂了", "全部用户都无法登录", "API 大面积超时"],
    "subscription": ["基础版套餐有什么", "企业版什么时候到期", "降级后还能使用 API 吗"],
    "human_ticket": ["帮我创建工单", "请提交高优支持工单", "这个问题转人工"],
}

_CONTEXT_SUFFIXES = ["", "，请给我操作步骤", "，生产环境遇到的", "，我们用的是 Python", "，租户是 demo-tenant"]

DEFAULT_SAAS_INTENT_CASES = [
    IntentTestCase(f"{seed}{suffix}", label)
    for label, seeds in _SEEDS.items()
    for seed in seeds
    for suffix in _CONTEXT_SUFFIXES
]

DEFAULT_SAAS_DIALOG_CASES = [
    {"question": "Python SDK 3.2.1 POST /v1/files 返回 403，我们刚降级成基础版", "expected_primary_agent": "integration"},
    {"question": "Webhook 在生产环境全部超时，request_id: req_8899", "expected_primary_agent": "incident"},
    {"question": "企业版是否支持 SSO，我们当前租户开启了吗", "expected_primary_agent": "customer_success"},
]

SAAS_MULTI_TURN_CASES = [
    {"turns": ["我想接入上传 API", "我使用 Python SDK", "现在返回 401，request_id: req_demo_01"]},
    {"turns": ["生产服务挂了", "影响了所有用户", "请帮我创建工单"]},
    {"turns": ["我要配置 Webhook", "验签一直失败", "生产环境全部回调都超时"]},
    {"turns": ["我们用 basic 套餐", "需要 batch_upload", "现在返回 403"]},
    {"turns": ["新用户怎么开始", "我是租户管理员", "第一步要配置 SSO"]},
    {"turns": ["企业版有什么功能", "我们的套餐快到期了", "可以继续用 API 吗"]},
    {"turns": ["Java SDK 上传失败", "版本是 3.2.1", "POST /v1/files 返回 429"]},
    {"turns": ["我们的区域配置是什么", "想看功能开关", "不需要修改，只查询"]},
    {"turns": ["查询工单 TR-DEMO1234", "它还在处理吗", "不要再创建新工单"]},
    {"turns": ["API 全部返回 500", "region 是 cn-east-1", "request_id: req_outage_01，请提交工单"]},
]

DEFAULT_SAAS_DIALOG_CASES.extend(SAAS_MULTI_TURN_CASES)

# 独立保留复合路由、工具故障和租户隔离用例，供单元/集成测试消费。
SAAS_COMPOSITE_CASES = [
    {
        "message": f"Python SDK 返回 403，套餐降级后发生，样例 {i}",
        "question": f"Python SDK 返回 403，套餐降级后发生，样例 {i}",
        "agents": ["integration", "subscription"],
        "expected_primary_agent": "integration",
        "expected_supporting_agents": ["subscription"],
    }
    for i in range(20)
]
SAAS_TOOL_FAILURE_CASES = [{"tool": "get_service_status", "failure": kind} for kind in ["timeout", "dns", "500", "invalid-json", "empty", "circuit-open", "403", "429", "connection-reset", "partial"]]
SAAS_TENANT_ISOLATION_CASES = [{"owner": "tenant-a", "caller": "tenant-b", "resource": f"ticket-{i}"} for i in range(10)]

DEFAULT_SAAS_DIALOG_CASES.extend(SAAS_COMPOSITE_CASES)
