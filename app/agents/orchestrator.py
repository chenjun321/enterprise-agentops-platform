from sqlalchemy.orm import Session

from app.agents.business_agents import ResultSynthesizer
from app.agents.executor import PlanExecutor
from app.agents.planner import PlannerAgent
from app.agents.router import RouterAgent
from app.core.state import AgentState
from app.memory.store import MemoryStore
from app.services.audit import AuditLogger
from app.tools.base import ToolRegistry
from app.tools.business_tools import (
    CRMTool,
    ExternalProfileTool,
    LogSearchTool,
    MarketingDataTool,
    OrderQueryTool,
    PaymentQueryTool,
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

    def run(self, state: AgentState) -> AgentState:
        state.long_memory = self.memory_store.list_memories(state.employee_id)
        self.audit.record(state, "memory_read", {"count": len(state.long_memory)})

        route = self.router.route(state)
        self.audit.record(state, "router_result", route)

        state.plan = self.planner.plan(state)
        self.audit.record(state, "plan_created", state.plan.model_dump())

        state = self.executor.execute(state)
        answer = self.synthesizer.synthesize(state)
        state.final_response = answer
        self.audit.record(state, "answer_created", {"target_agent": state.target_agent, "intent": state.intent})

        candidate = self.memory_store.infer_memory_candidate(state.employee_id, state.message)
        if candidate:
            memory = self.memory_store.create_memory(**candidate)
            self.audit.record(state, "memory_written", {"memory_id": memory["id"], "memory_type": memory["memory_type"]})

        return state

    def _build_registry(self, db: Session) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(CRMTool(db))
        registry.register(ExternalProfileTool())
        registry.register(MarketingDataTool(db))
        registry.register(OrderQueryTool(db))
        registry.register(PaymentQueryTool(db))
        registry.register(LogSearchTool(db))
        registry.register(KnowledgeSearchTool(db))
        registry.register(CodeSearchTool())
        registry.register(SQLSelectTool(db))
        return registry

