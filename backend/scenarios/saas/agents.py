"""B2B SaaS 五类 Agent：共用基类，但有独立契约和工具白名单。"""

from __future__ import annotations

import json
import re
import time

from agents.agent_orchestrator import AgentProfile, AgentResponse, AgentType, BaseAgent, Request


class SaaSToolScopeMixin:
    def get_tools(self):
        all_tools = super().get_tools()
        return {name: spec for name, spec in all_tools.items() if name in self.profile.tool_scope}


class CustomerSuccessAgent(SaaSToolScopeMixin, BaseAgent):
    agent_type = AgentType.CUSTOMER_SUCCESS
    profile = AgentProfile(
        role="B2B SaaS 客户成功顾问",
        mission="解释产品功能、完成新用户引导，并识别需要专业支持的问题。",
        workflow=("确认目标", "查询产品文档", "区分功能与套餐权限", "给出下一步"),
        input_contract=("租户", "产品", "用户目标", "文档来源"),
        output_contract=("直接回答", "引用可用文档", "不编造功能和权限"),
        handoff_conditions=("涉及技术故障、套餐变更或人工操作",),
        tool_scope=("search_product_docs", "lookup_tenant_config", "check_subscription"),
        temperature=0.25, max_tokens=1000,
    )
    system_prompt = "你是 AcmeCloud 客户成功顾问。只根据工具和文档中的可核验信息回答。"


class IntegrationAgent(SaaSToolScopeMixin, BaseAgent):
    agent_type = AgentType.INTEGRATION
    profile = AgentProfile(
        role="API/SDK 集成支持工程师",
        mission="根据接口、SDK、错误码和环境信息给出低风险、可验证的排障步骤。",
        workflow=("确认请求", "查询错误目录", "检索对应版本文档", "检查权限与状态", "给出验证方法"),
        input_contract=("request_id", "api_path", "HTTP 方法", "SDK 语言与版本", "环境"),
        output_contract=("现象复述", "可能原因", "编号排查步骤", "验证方法"),
        handoff_conditions=("持续 5xx、生产大面积影响、需要后台日志",),
        tool_scope=("search_product_docs", "lookup_api_error", "get_service_status", "check_subscription"),
        temperature=0.05, max_tokens=1300,
    )
    system_prompt = "你是 AcmeCloud API/SDK 集成支持工程师。不要声称读取了未提供的内部日志。"


class SubscriptionAgent(SaaSToolScopeMixin, BaseAgent):
    agent_type = AgentType.SUBSCRIPTION
    profile = AgentProfile(
        role="SaaS 订阅与权限专员",
        mission="查询套餐、配额和功能权限，解释可核验的订阅事实。",
        workflow=("确认目标功能", "查询真实套餐", "核对租户开关", "说明边界"),
        input_contract=("租户", "套餐", "目标功能", "到期时间"),
        output_contract=("当前套餐", "权限结论", "配额", "下一步"),
        handoff_conditions=("套餐变更、合同、价格或退费操作",),
        tool_scope=("check_subscription", "lookup_tenant_config", "search_product_docs"),
        temperature=0.0, max_tokens=1000,
    )
    system_prompt = "你是 AcmeCloud 订阅与权限专员。不执行套餐变更或退款。"


class IncidentAgent(SaaSToolScopeMixin, BaseAgent):
    agent_type = AgentType.INCIDENT
    profile = AgentProfile(
        role="SaaS 故障响应协调员",
        mission="判断服务影响范围，查询已配置服务状态，给出保守的故障应对建议。",
        workflow=("确认环境与影响", "查询服务状态", "区分局部与平台故障", "保留 request_id", "必要时升级"),
        input_contract=("环境", "区域", "服务", "影响范围", "request_id"),
        output_contract=("检查时间", "服务状态", "当前判断", "建议动作"),
        handoff_conditions=("生产大面积不可用、数据丢失、安全事件",),
        tool_scope=("get_service_status", "lookup_api_error", "search_product_docs"),
        temperature=0.0, max_tokens=1000,
    )
    system_prompt = "你是 AcmeCloud 故障响应协调员。只能把工具实际返回的状态当作服务事实。"


class TicketAgent(SaaSToolScopeMixin, BaseAgent):
    agent_type = AgentType.TICKET
    profile = AgentProfile(
        role="人工支持工单节点",
        mission="在用户明确要求时生成可审计、幂等的支持工单。",
        workflow=("确认明确意图", "整理已知信息", "确定优先级", "创建或查询工单"),
        input_contract=("租户", "request_id", "问题摘要", "优先级"),
        output_contract=("工单编号", "状态", "是否新建", "后续说明"),
        handoff_conditions=(),
        tool_scope=("create_support_ticket", "get_ticket_status"),
        temperature=0.0, max_tokens=500,
    )
    system_prompt = "你是工单交接节点。不要编造工单号。"

    async def handle(self, req: Request) -> AgentResponse:
        """写操作不交给模型自由决定：先做明确意图校验，再直接调用工具。"""
        started = time.monotonic()
        self.stats.total += 1
        explicit_create = any(
            phrase in req.message.lower()
            for phrase in ["创建工单", "提交工单", "转人工", "create ticket"]
        )
        ticket_ids = req.entities.get("ticket_id", []) or re.findall(r"\bTR-[A-Z0-9]{4,32}\b", req.message, re.I)
        tool_name = "create_support_ticket" if explicit_create else "get_ticket_status"
        tool = self.get_tools().get(tool_name)
        if tool is None:
            return AgentResponse(self.agent_type, "工单服务尚未就绪。", False)
        if explicit_create:
            priority = "critical" if getattr(req.urgency, "name", "") == "CRITICAL" else "high" if getattr(req.urgency, "name", "") == "HIGH" else "medium"
            title = req.message.strip().replace("\n", " ")[:80] or "AcmeCloud 支持请求"
            payload = {"title": title, "description": json.dumps({
                "message": req.message, "intent": req.intent.value if req.intent else None,
                "entities": req.entities, "environment": req.environment,
            }, ensure_ascii=False), "priority": priority}
        elif ticket_ids:
            payload = {"ticket_id": ticket_ids[0].upper()}
        else:
            self.stats.success += 1
            self.stats.total_ms += (time.monotonic() - started) * 1000
            return AgentResponse(self.agent_type, "请提供要查询的工单编号（例如 TR-XXXXXXXXXX）。", True)
        result = await tool.handler(req, payload)
        ms = (time.monotonic() - started) * 1000
        success = bool(result.get("success"))
        self.stats.total_ms += ms
        if success:
            self.stats.success += 1
        ticket_id = result.get("ticket_id")
        if success and ticket_id:
            verb = "已创建支持工单" if explicit_create else "工单"
            content = f"{verb} {ticket_id}，当前状态：{result.get('status', 'open')}。"
        elif not explicit_create and result.get("found") is False:
            content = "未找到该工单，或它不属于当前租户。"
        else:
            content = f"暂未能{'创建' if explicit_create else '查询'}工单：{result.get('error', '未知错误')}"
        return AgentResponse(
            self.agent_type, content, success, latency_ms=ms, escalate=explicit_create,
            tools_used=[tool_name] if success else [],
            tool_traces=[{"agent_type": self.agent_type.value, "tool_name": tool_name,
                          "success": success, "ticket_id": ticket_id, "error": result.get("error", "")}],
        )
