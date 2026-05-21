from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    employee_id: Optional[str] = Field(default=None, examples=["employee_support_001"])
    role: Optional[str] = Field(default=None, examples=["support", "sales", "marketing", "engineer"])
    message: str
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class CustomerQARequest(BaseModel):
    customer_user_id: Optional[str] = Field(default=None, examples=["customer_002"])
    contact: Optional[str] = Field(default=None, examples=["user@example.com"])
    channel: str = Field(default="web")
    message: str
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    thread_id: str
    target_agent: str
    intent: str
    answer: Dict[str, Any]
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    plan: Dict[str, Any]
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)


class CustomerQAResponse(BaseModel):
    session_id: str
    thread_id: str
    intent: str
    answer: Dict[str, Any]
    ticket: Optional[Dict[str, Any]] = None


class MemoryCreateRequest(BaseModel):
    employee_id: Optional[str] = None
    memory_type: str
    content: str
    source: str = "explicit_user_request"


class MemoryResponse(BaseModel):
    memories: List[Dict[str, Any]]


class MeResponse(BaseModel):
    employee_id: str
    role: str
    auth_mode: str
