"""SaaS 场景编排器：复用 TenantRelay 基类，只替换 Agent 池和路由策略。"""

from __future__ import annotations

from typing import Dict, List

from anthropic import AsyncAnthropic

from agents.agent_orchestrator import AgentOrchestrator, AgentType, RoutingDecision
from core.intent_recognizer import IntentCategory, IntentRecognizer, UrgencyLevel
from scenarios.saas.agents import CustomerSuccessAgent, IncidentAgent, IntegrationAgent, SubscriptionAgent, TicketAgent


class SaaSAgentOrchestrator(AgentOrchestrator):
    def __init__(self, api_key: str, base_url=None, model="claude-3-5-sonnet-20241022", skill_manager=None):
        super().__init__(api_key, base_url, model, skill_manager)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = AsyncAnthropic(**kwargs)
        self._intent_recognizer = IntentRecognizer(api_key, base_url, model, scenario="saas")
        self._pool = {
            AgentType.CUSTOMER_SUCCESS: [self._make_agent(CustomerSuccessAgent, client, model, skill_manager)],
            AgentType.INTEGRATION: [self._make_agent(IntegrationAgent, client, model, skill_manager)],
            AgentType.SUBSCRIPTION: [self._make_agent(SubscriptionAgent, client, model, skill_manager)],
            AgentType.INCIDENT: [self._make_agent(IncidentAgent, client, model, skill_manager)],
            AgentType.TICKET: [self._make_agent(TicketAgent, client, model, skill_manager)],
        }
        self.set_shared_tools({})

    def _route_decision(self, req):
        intents = {req.intent, *req.secondary_intents}
        if IntentCategory.HUMAN_TICKET in intents and IntentCategory.INCIDENT_REPORT in intents:
            return RoutingDecision(
                AgentType.INCIDENT, [AgentType.TICKET],
                reason="故障与明确工单请求并存，先做故障响应并同时创建工单",
                confidence=max(req.intent_confidence, 0.9),
            )
        integration_intents = {
            IntentCategory.API_INTEGRATION, IntentCategory.SDK_ERROR,
        }
        subscription_intents = {
            IntentCategory.PERMISSION_REQUEST, IntentCategory.SUBSCRIPTION,
        }
        if intents & integration_intents and intents & subscription_intents:
            return RoutingDecision(
                AgentType.INTEGRATION, [AgentType.SUBSCRIPTION],
                reason="API/SDK 问题与套餐权限并存，技术排查为主、订阅核验为辅",
                confidence=max(req.intent_confidence, 0.9),
            )
        if IntentCategory.FEATURE_INQUIRY in intents and intents & subscription_intents:
            return RoutingDecision(
                AgentType.CUSTOMER_SUCCESS, [AgentType.SUBSCRIPTION],
                reason="功能咨询与套餐差异并存，客户成功为主、订阅核验为辅",
                confidence=max(req.intent_confidence, 0.88),
            )
        if req.intent == IntentCategory.HUMAN_TICKET:
            return RoutingDecision(AgentType.TICKET, reason="用户要求创建或查询支持工单", confidence=max(req.intent_confidence, 0.9))

        scores = self._domain_scores(req)
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        primary, primary_score = ordered[0]
        targets = self._collaboration_targets(req)
        supporting = [item for item in targets if item != primary and self._pool.get(item)]
        reason = self._routing_reason(req, scores, primary, supporting)
        return RoutingDecision(primary, supporting, reason, round(min(primary_score, 1.0), 3))

    def _domain_scores(self, req) -> Dict[AgentType, float]:
        msg = req.message.lower()
        scores = {AgentType.CUSTOMER_SUCCESS: 0.1, AgentType.INTEGRATION: 0.0,
                  AgentType.SUBSCRIPTION: 0.0, AgentType.INCIDENT: 0.0, AgentType.TICKET: 0.0}
        if req.intent in {IntentCategory.FEATURE_INQUIRY, IntentCategory.ONBOARDING, IntentCategory.TENANT_CONFIGURATION,
                          IntentCategory.GREETING, IntentCategory.FEEDBACK, IntentCategory.COMPLAINT, IntentCategory.OTHER}:
            scores[AgentType.CUSTOMER_SUCCESS] += 0.75
        if req.intent in {IntentCategory.API_INTEGRATION, IntentCategory.SDK_ERROR}:
            scores[AgentType.INTEGRATION] += 0.75
        if req.intent == IntentCategory.WEBHOOK_FAILURE:
            # Webhook 失败先由故障节点判断影响，集成节点负责验签/配置排查。
            scores[AgentType.INCIDENT] += 0.95
            scores[AgentType.INTEGRATION] += 0.5
        if req.intent in {IntentCategory.SUBSCRIPTION, IntentCategory.PERMISSION_REQUEST}:
            scores[AgentType.SUBSCRIPTION] += 0.75
        if req.intent == IntentCategory.INCIDENT_REPORT or req.urgency == UrgencyLevel.CRITICAL:
            scores[AgentType.INCIDENT] += 0.9
        keyword_groups = {
            AgentType.INTEGRATION: ["api", "sdk", "webhook", "401", "403", "500", "接口", "回调"],
            AgentType.SUBSCRIPTION: ["套餐", "订阅", "权限", "配额", "企业版", "基础版", "降级"],
            AgentType.INCIDENT: ["故障", "服务挂", "全部超时", "outage", "production down"],
            AgentType.TICKET: ["创建工单", "提交工单", "转人工"],
            AgentType.CUSTOMER_SUCCESS: ["功能", "怎么用", "接入", "新用户"],
        }
        for agent_type, keywords in keyword_groups.items():
            scores[agent_type] += min(0.45, sum(1 for word in keywords if word in msg) * 0.15)
        if req.entities.get("error_code") or req.entities.get("api_path"):
            scores[AgentType.INTEGRATION] += 0.2
        if req.entities.get("plan_name"):
            scores[AgentType.SUBSCRIPTION] += 0.2
        # Monitor 惩罚真正进入领域路由，而不只用于同类实例择优。
        for agent_type in list(scores):
            agent = self._best_agent(agent_type)
            if agent:
                scores[agent_type] *= max(0.0, 1.0 - agent.stats.monitor_penalty)
        return {key: round(value, 3) for key, value in scores.items()}

    def _collaboration_targets(self, req) -> List[AgentType]:
        intents = {req.intent, *req.secondary_intents}
        targets = []
        if intents & {IntentCategory.API_INTEGRATION, IntentCategory.SDK_ERROR, IntentCategory.WEBHOOK_FAILURE}:
            targets.append(AgentType.INTEGRATION)
        if intents & {IntentCategory.SUBSCRIPTION, IntentCategory.PERMISSION_REQUEST}:
            targets.append(AgentType.SUBSCRIPTION)
        if IntentCategory.INCIDENT_REPORT in intents or req.urgency == UrgencyLevel.CRITICAL:
            targets.append(AgentType.INCIDENT)
        if IntentCategory.HUMAN_TICKET in intents:
            targets.append(AgentType.TICKET)
        if intents & {IntentCategory.FEATURE_INQUIRY, IntentCategory.ONBOARDING, IntentCategory.TENANT_CONFIGURATION}:
            targets.append(AgentType.CUSTOMER_SUCCESS)
        return list(dict.fromkeys(targets))
