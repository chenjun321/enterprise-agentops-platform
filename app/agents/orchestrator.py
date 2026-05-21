from sqlalchemy.orm import Session

from app.agents.business_agents import ResultSynthesizer
from app.agents.executor import PlanExecutor
from app.agents.planner import PlannerAgent
from app.agents.router import RouterAgent
from app.core.state import AgentState
from app.memory.store import MemoryStore
from app.services.audit import AuditLogger
from app.services.reflection import ReflectionService
from app.services.thread_context import ThreadContextService
from app.tools.base import ToolRegistry
from app.tools.business_tools import (
    CRMTool,
    CustomerIdentityResolveTool,
    ExternalProfileTool,
    LogSearchTool,
    MarketingDataTool,
    OrderQueryTool,
    PaymentQueryTool,
    SupportTicketCreateTool,
)
from app.tools.code_search_tool import CodeSearchTool
from app.tools.knowledge_search_tool import KnowledgeSearchTool
from app.tools.sql_tool import SQLSelectTool


class AgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.memory_store = MemoryStore(db)
        self.audit = AuditLogger(db)
        self.router = RouterAgent()
        self.planner = PlannerAgent()
        self.registry = self._build_registry(db)
        self.executor = PlanExecutor(self.registry)
        self.synthesizer = ResultSynthesizer()
        self.reflection = ReflectionService(db)
        self.thread_context = ThreadContextService(db)

    def run(self, state: AgentState) -> AgentState:
        state.long_memory = self.memory_store.list_memories(state.employee_id)
        self.audit.record(state, "memory_read", {"count": len(state.long_memory)})

        route = self.router.route(state)
        self.audit.record(state, "router_result", route)

        state.plan = self.planner.plan(state)
        self.audit.record(state, "plan_created", state.plan.model_dump())

        state = self.executor.execute(state)
        if state.final_response and state.final_response.get("type") == "needs_user_input":
            pending = self.thread_context.open_pending_input(
                thread_id=state.session_id,
                target_agent=state.target_agent,
                intent=state.intent,
                missing_fields=state.plan.missing_fields if state.plan else [],
            )
            state.final_response.update(
                {
                    "question": pending.question,
                    "resume_policy": "continue_after_user_reply",
                    "thread_status": "waiting_for_input",
                }
            )
        answer = self.synthesizer.synthesize(state)
        state.final_response = answer
        self.audit.record(state, "answer_created", {"target_agent": state.target_agent, "intent": state.intent})
        reflection = self.reflection.reflect(state, answer)
        state.final_response = reflection.final_answer
        self.audit.record(
            state,
            "reflection_completed",
            {
                "passed": reflection.passed,
                "risk_level": reflection.risk_level,
                "rewrite_required": reflection.rewrite_required,
                "failed_checks": [check.name for check in reflection.checks if not check.passed],
            },
        )

        candidate = self.memory_store.infer_memory_candidate(state.employee_id, state.message)
        if candidate:
            memory = self.memory_store.create_memory(**candidate)
            self.audit.record(state, "memory_written", {"memory_id": memory["id"], "memory_type": memory["memory_type"]})

        self.db.commit()
        return state

    def _build_registry(self, db: Session) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(CRMTool(db))
        registry.register(ExternalProfileTool())
        registry.register(MarketingDataTool(db))
        registry.register(OrderQueryTool(db))
        registry.register(PaymentQueryTool(db))
        registry.register(LogSearchTool(db))
        registry.register(CustomerIdentityResolveTool(db))
        registry.register(SupportTicketCreateTool(db))
        registry.register(KnowledgeSearchTool(db))
        registry.register(CodeSearchTool())
        registry.register(SQLSelectTool(db))
        return registry
