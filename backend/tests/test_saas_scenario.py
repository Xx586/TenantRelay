import asyncio
from types import SimpleNamespace

import pytest

from agents.agent_orchestrator import AgentType, Request
from agents.tools import make_tool
from core.intent_recognizer import IntentCategory, IntentRecognizer, UrgencyLevel
from scenarios.saas.agents import CustomerSuccessAgent, IncidentAgent, IntegrationAgent, SubscriptionAgent, TicketAgent
from scenarios.saas.orchestrator import SaaSAgentOrchestrator
from evaluation.evaluator import EndToEndEvaluator
from evaluation.saas_cases import (
    DEFAULT_SAAS_INTENT_CASES, SAAS_COMPOSITE_CASES, SAAS_MULTI_TURN_CASES,
    SAAS_TENANT_ISOLATION_CASES, SAAS_TOOL_FAILURE_CASES,
)


class FakeClient:
    class Messages:
        async def create(self, **kwargs):
            raise RuntimeError("not used")
    messages = Messages()


def test_saas_pattern_covers_all_ten_intents():
    recognizer = IntentRecognizer("test-key", scenario="saas")
    cases = {
        "这个功能支持吗": IntentCategory.FEATURE_INQUIRY,
        "新用户如何开始使用": IntentCategory.ONBOARDING,
        "API 接口怎么调用": IntentCategory.API_INTEGRATION,
        "Python SDK 报错": IntentCategory.SDK_ERROR,
        "Webhook 回调失败": IntentCategory.WEBHOOK_FAILURE,
        "403 权限不足": IntentCategory.PERMISSION_REQUEST,
        "查看租户配置": IntentCategory.TENANT_CONFIGURATION,
        "生产服务挂了": IntentCategory.INCIDENT_REPORT,
        "基础版套餐有什么": IntentCategory.SUBSCRIPTION,
        "帮我创建工单": IntentCategory.HUMAN_TICKET,
    }
    for message, expected in cases.items():
        assert recognizer._pattern_recognize(message)["intent"] is expected


def test_saas_entities_and_secondary_intents():
    recognizer = IntentRecognizer("test-key", scenario="saas")
    message = "tenant_id: acme-01 Python SDK 3.2.1 POST /v1/files 返回 403，套餐刚降级成基础版，request_id: req_8899"
    entities = recognizer._extract_entities(message)
    secondary = recognizer._secondary_intents(message, IntentCategory.SDK_ERROR)
    assert entities["tenant_id"] == ["acme-01"]
    assert entities["request_id"] == ["req_8899"]
    assert entities["api_path"] == ["/v1/files"]
    assert entities["http_method"] == ["POST"]
    assert entities["sdk_language"] == ["python"]
    assert "403" in entities["error_code"]
    assert IntentCategory.SUBSCRIPTION in secondary
    assert IntentCategory.PERMISSION_REQUEST in secondary


def test_all_saas_entities_are_extracted_and_rules_win_over_llm():
    recognizer = IntentRecognizer("test-key", scenario="saas")
    message = (
        "tenant_id: acme-01 request_id: req_7788 Python SDK version 3.2.1 "
        "PATCH /v2/webhooks in production cn-east-1 returns 500; "
        "basic plan callback https://hooks.example.com/events?token=do-not-store auth service"
    )
    entities = recognizer._extract_entities(message)
    assert entities["tenant_id"] == ["acme-01"]
    assert entities["request_id"] == ["req_7788"]
    assert "/v2/webhooks" in entities["api_path"]
    assert entities["http_method"] == ["PATCH"]
    assert entities["sdk_language"] == ["python"]
    assert entities["sdk_version"] == ["3.2.1"]
    assert entities["region"] == ["cn-east-1"]
    assert entities["plan_name"] == ["basic"]
    assert entities["environment"] == ["production"]
    assert entities["webhook_url_host"] == ["hooks.example.com"]
    assert set(entities["service_name"]) >= {"auth", "webhook"}

    merged = recognizer._merge_llm_entities(entities, {
        "tenant_id": ["wrong-tenant"],
        "service_name": ["token=secret"],
    })
    assert merged["tenant_id"] == ["acme-01"]
    assert "token=secret" not in merged["service_name"]


def test_saas_agents_have_isolated_tool_scopes():
    available = {
        name: object() for name in [
            "search_product_docs", "lookup_api_error", "get_service_status",
            "lookup_tenant_config", "check_subscription", "create_support_ticket", "get_ticket_status",
        ]
    }
    agents = [CustomerSuccessAgent(FakeClient(), "test"), IntegrationAgent(FakeClient(), "test"),
              SubscriptionAgent(FakeClient(), "test"), IncidentAgent(FakeClient(), "test"), TicketAgent(FakeClient(), "test")]
    for agent in agents:
        agent.set_shared_tools(available)
        assert set(agent.get_tools()) == set(agent.profile.tool_scope)
    assert "create_support_ticket" not in agents[0].get_tools()
    assert set(agents[-1].get_tools()) == {"create_support_ticket", "get_ticket_status"}


def test_composite_sdk_and_plan_routes_to_two_agents():
    orchestrator = SaaSAgentOrchestrator.__new__(SaaSAgentOrchestrator)
    def agent():
        return SimpleNamespace(stats=SimpleNamespace(monitor_penalty=0.0, routing_score=lambda: 1.0))
    orchestrator._pool = {kind: [agent()] for kind in [
        AgentType.CUSTOMER_SUCCESS, AgentType.INTEGRATION, AgentType.SUBSCRIPTION,
        AgentType.INCIDENT, AgentType.TICKET,
    ]}
    req = Request(
        message="Python SDK 返回 403，我们刚降级到基础版",
        user_id="u1", conv_id="c1", tenant_id="demo-tenant",
        intent=IntentCategory.SDK_ERROR, intent_group="api_integration",
        urgency=UrgencyLevel.LOW, intent_confidence=0.9,
        secondary_intents=[IntentCategory.PERMISSION_REQUEST, IntentCategory.SUBSCRIPTION],
        entities={"error_code": ["403"], "sdk_language": ["python"], "plan_name": ["基础版"]},
    )
    decision = orchestrator._route_decision(req)
    assert decision.primary_agent is AgentType.INTEGRATION
    assert AgentType.SUBSCRIPTION in decision.supporting_agents


@pytest.mark.parametrize("case", SAAS_COMPOSITE_CASES)
def test_all_composite_eval_cases_route_to_expected_agents(case):
    orchestrator = SaaSAgentOrchestrator.__new__(SaaSAgentOrchestrator)
    def agent():
        return SimpleNamespace(stats=SimpleNamespace(monitor_penalty=0.0, routing_score=lambda: 1.0))
    orchestrator._pool = {kind: [agent()] for kind in [
        AgentType.CUSTOMER_SUCCESS, AgentType.INTEGRATION, AgentType.SUBSCRIPTION,
        AgentType.INCIDENT, AgentType.TICKET,
    ]}
    req = Request(
        message=case["message"], user_id="u", conv_id="c",
        intent=IntentCategory.SDK_ERROR, urgency=UrgencyLevel.LOW,
        secondary_intents=[IntentCategory.PERMISSION_REQUEST, IntentCategory.SUBSCRIPTION],
    )
    decision = orchestrator._route_decision(req)
    assert decision.primary_agent.value == case["expected_primary_agent"]
    assert set(case["expected_supporting_agents"]).issubset(
        {agent_type.value for agent_type in decision.supporting_agents}
    )


def test_composite_routes_are_stable_even_when_secondary_domain_is_primary_intent():
    orchestrator = SaaSAgentOrchestrator.__new__(SaaSAgentOrchestrator)
    def agent():
        return SimpleNamespace(stats=SimpleNamespace(monitor_penalty=0.0, routing_score=lambda: 1.0))
    orchestrator._pool = {kind: [agent()] for kind in [
        AgentType.CUSTOMER_SUCCESS, AgentType.INTEGRATION, AgentType.SUBSCRIPTION,
        AgentType.INCIDENT, AgentType.TICKET,
    ]}

    permission_first = Request(
        message="API 返回 403，是套餐权限吗", user_id="u", conv_id="c",
        intent=IntentCategory.PERMISSION_REQUEST, urgency=UrgencyLevel.LOW,
        secondary_intents=[IntentCategory.API_INTEGRATION, IntentCategory.SUBSCRIPTION],
    )
    decision = orchestrator._route_decision(permission_first)
    assert decision.primary_agent is AgentType.INTEGRATION
    assert decision.supporting_agents == [AgentType.SUBSCRIPTION]

    plan_first = Request(
        message="这个功能支持吗，基础版和企业版有什么差异", user_id="u", conv_id="c2",
        intent=IntentCategory.SUBSCRIPTION, urgency=UrgencyLevel.LOW,
        secondary_intents=[IntentCategory.FEATURE_INQUIRY],
    )
    decision = orchestrator._route_decision(plan_first)
    assert decision.primary_agent is AgentType.CUSTOMER_SUCCESS
    assert decision.supporting_agents == [AgentType.SUBSCRIPTION]


def test_monitor_penalty_affects_saas_domain_score():
    orchestrator = SaaSAgentOrchestrator.__new__(SaaSAgentOrchestrator)
    def agent(penalty):
        return SimpleNamespace(stats=SimpleNamespace(monitor_penalty=penalty, routing_score=lambda: 1.0 - penalty))
    orchestrator._pool = {
        AgentType.CUSTOMER_SUCCESS: [agent(0.0)], AgentType.INTEGRATION: [agent(0.8)],
        AgentType.SUBSCRIPTION: [agent(0.0)], AgentType.INCIDENT: [agent(0.0)], AgentType.TICKET: [agent(0.0)],
    }
    req = Request(message="API 调用问题", user_id="u", conv_id="c", intent=IntentCategory.API_INTEGRATION,
                  urgency=UrgencyLevel.LOW, entities={})
    scores = orchestrator._domain_scores(req)
    assert scores[AgentType.INTEGRATION] < 0.3


def test_webhook_failure_routes_incident_primary_integration_supporting():
    orchestrator = SaaSAgentOrchestrator.__new__(SaaSAgentOrchestrator)
    def agent():
        return SimpleNamespace(stats=SimpleNamespace(monitor_penalty=0.0, routing_score=lambda: 1.0))
    orchestrator._pool = {kind: [agent()] for kind in [
        AgentType.CUSTOMER_SUCCESS, AgentType.INTEGRATION, AgentType.SUBSCRIPTION,
        AgentType.INCIDENT, AgentType.TICKET,
    ]}
    req = Request(
        message="Webhook 回调失败", user_id="u", conv_id="c",
        intent=IntentCategory.WEBHOOK_FAILURE, urgency=UrgencyLevel.LOW, entities={},
    )
    decision = orchestrator._route_decision(req)
    assert decision.primary_agent is AgentType.INCIDENT
    assert AgentType.INTEGRATION in decision.supporting_agents


def test_ticket_agent_queries_existing_ticket_without_creating():
    calls = []
    async def create_handler(req, args):
        calls.append("create")
        return {"success": True, "ticket_id": "TR-WRONG", "status": "open"}
    async def get_handler(req, args):
        calls.append("get")
        return {"success": True, "ticket_id": args["ticket_id"], "status": "pending"}

    agent = TicketAgent(FakeClient(), "test")
    agent.set_shared_tools({
        "create_support_ticket": make_tool("create_support_ticket", "", {}, create_handler),
        "get_ticket_status": make_tool("get_ticket_status", "", {"ticket_id": {"type": "string"}}, get_handler),
    })
    req = Request(
        message="查询工单 TR-ABC123 的进度", user_id="u", conv_id="c",
        intent=IntentCategory.HUMAN_TICKET, urgency=UrgencyLevel.LOW,
        entities={"ticket_id": ["TR-ABC123"]},
    )
    result = asyncio.run(agent.handle(req))
    assert calls == ["get"]
    assert "pending" in result.content
    assert result.escalate is False


def test_saas_eval_dataset_meets_minimum_coverage():
    by_intent = {}
    for case in DEFAULT_SAAS_INTENT_CASES:
        by_intent[case.expected_intent] = by_intent.get(case.expected_intent, 0) + 1
    assert len(by_intent) == 10
    assert min(by_intent.values()) >= 15
    assert len(SAAS_COMPOSITE_CASES) >= 20
    assert len(SAAS_MULTI_TURN_CASES) >= 10
    assert len(SAAS_TOOL_FAILURE_CASES) >= 10
    assert len(SAAS_TENANT_ISOLATION_CASES) >= 10


def test_tool_success_metric_counts_transport_and_business_failure():
    traces = [
        {"success": True, "result_success": True},
        {"success": True, "result_success": False},
        {"success": False, "result_success": None},
    ]
    assert EndToEndEvaluator._tool_trace_success_rate(traces) == 0.3333
    assert EndToEndEvaluator._tool_trace_success_rate([]) is None
