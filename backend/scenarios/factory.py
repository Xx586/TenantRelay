"""场景工厂：把原客服与 B2B SaaS 的初始化差异收口在一处。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ScenarioRuntime:
    name: str
    orchestrator: Any
    recognizer: Any
    skills_dir: Path
    store: Optional[Any] = None
    ticket_service: Optional[Any] = None
    settings: Optional[Any] = None

    def attach_tools(self, tool_manager: Any) -> None:
        """知识工具在 ChromaDB 初始化后注入，避免场景工厂绑定启动顺序。"""
        if self.name == "saas":
            from scenarios.saas.tools import build_saas_tools

            self.orchestrator.set_shared_tools(
                build_saas_tools(self.store, self.ticket_service, tool_manager)
            )
        else:
            from agents.agent_orchestrator import build_shared_rag_tools

            self.orchestrator.set_shared_tools(build_shared_rag_tools(tool_manager))


def scenario_skills_dir(scenario: str, project_root: str) -> Path:
    """由场景工厂统一决定 Skill 包路径。"""
    name = scenario.strip().lower()
    if name == "saas":
        return Path(project_root) / "scenarios" / "saas" / "skills"
    if name == "customer_support":
        return Path(project_root) / "skills"
    raise ValueError("TENANTRELAY_SCENARIO 只能是 customer_support 或 saas")


async def create_scenario_runtime(
    scenario: str,
    cfg: dict,
    skill_manager: Any,
    project_root: str,
) -> ScenarioRuntime:
    """按场景创建编排器、意图识别器与可选 SaaS 数据层。"""
    from agents.agent_orchestrator import AgentOrchestrator
    from core.intent_recognizer import IntentRecognizer

    name = scenario.strip().lower()
    if name not in {"customer_support", "saas"}:
        raise ValueError("TENANTRELAY_SCENARIO 只能是 customer_support 或 saas")

    recognizer = IntentRecognizer(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        model=cfg["model"],
        scenario=name,
    )
    if name == "customer_support":
        orchestrator = AgentOrchestrator(
            api_key=cfg["api_key"],
            base_url=cfg.get("base_url"),
            model=cfg["model"],
            skill_manager=skill_manager,
        )
        return ScenarioRuntime(
            name=name,
            orchestrator=orchestrator,
            recognizer=recognizer,
            skills_dir=scenario_skills_dir(name, project_root),
        )

    from scenarios.saas.config import SaaSSettings
    from scenarios.saas.orchestrator import SaaSAgentOrchestrator
    from scenarios.saas.store import SaaSStore
    from scenarios.saas.ticketing import TicketService

    settings = SaaSSettings.from_env()
    store = SaaSStore(settings.database_url)
    await store.initialize(settings.demo_tenant_id, settings.demo_api_key)
    ticket_service = TicketService(store, settings)
    orchestrator = SaaSAgentOrchestrator(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        model=cfg["model"],
        skill_manager=skill_manager,
    )
    return ScenarioRuntime(
        name=name,
        orchestrator=orchestrator,
        recognizer=recognizer,
        skills_dir=scenario_skills_dir(name, project_root),
        store=store,
        ticket_service=ticket_service,
        settings=settings,
    )
