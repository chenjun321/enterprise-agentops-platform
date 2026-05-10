from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


AgentName = Literal["sales_agent", "marketing_agent", "customer_qa_agent", "unknown"]


class AuditItem(BaseModel):
    event_type: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanStep(BaseModel):
    step_id: str
    type: Literal["tool_call", "analysis", "safety_check", "human_approval"]
    name: str
    tool: Optional[str] = None
    agent: Optional[str] = None
    input: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    required: bool = True


class ExecutionPlan(BaseModel):
    plan_id: str
    target_agent: AgentName
    intent: str
    steps: List[PlanStep]
    needs_user_input: bool = False
    missing_fields: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    session_id: str = Field(default_factory=lambda: f"sess_{uuid4().hex[:12]}")
    employee_id: str
    role: str
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    long_memory: List[Dict[str, Any]] = Field(default_factory=list)
    target_agent: AgentName = "unknown"
    intent: str = "unknown"
    plan: Optional[ExecutionPlan] = None
    step_results: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    final_response: Optional[Dict[str, Any]] = None
    audit_events: List[AuditItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_audit(self, event_type: str, detail: Dict[str, Any]) -> None:
        self.audit_events.append(AuditItem(event_type=event_type, detail=detail))
        self.updated_at = datetime.utcnow()

