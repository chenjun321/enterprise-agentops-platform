from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    employee_id: str = Field(..., examples=["employee_support_001"])
    role: str = Field(..., examples=["support", "sales", "marketing", "engineer"])
    message: str
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    target_agent: str
    intent: str
    answer: Dict[str, Any]
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    plan: Dict[str, Any]
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryCreateRequest(BaseModel):
    employee_id: str
    memory_type: str
    content: str
    source: str = "explicit_user_request"


class MemoryResponse(BaseModel):
    memories: List[Dict[str, Any]]

