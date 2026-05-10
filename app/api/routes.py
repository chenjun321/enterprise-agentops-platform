from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.core.state import AgentState
from app.db.database import get_db
from app.memory.store import MemoryStore
from app.schemas.api import ChatRequest, ChatResponse, MemoryCreateRequest, MemoryResponse


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    initial = AgentState(employee_id=request.employee_id, role=request.role, message=request.message)
    state = AgentState(
        session_id=request.session_id or initial.session_id,
        employee_id=request.employee_id,
        role=request.role,
        message=request.message,
        context=request.context,
    )
    orchestrator = AgentOrchestrator(db)
    state = orchestrator.run(state)
    return ChatResponse(
        session_id=state.session_id,
        target_agent=state.target_agent,
        intent=state.intent,
        answer=state.final_response or {},
        evidence=state.evidence,
        plan=state.plan.model_dump() if state.plan else {},
        audit_events=[item.model_dump() for item in state.audit_events],
    )


@router.post("/memory", response_model=MemoryResponse)
def create_memory(request: MemoryCreateRequest, db: Session = Depends(get_db)) -> MemoryResponse:
    memory = MemoryStore(db).create_memory(
        employee_id=request.employee_id,
        memory_type=request.memory_type,
        content=request.content,
        source=request.source,
    )
    return MemoryResponse(memories=[memory])


@router.get("/memory/{employee_id}", response_model=MemoryResponse)
def list_memory(employee_id: str, db: Session = Depends(get_db)) -> MemoryResponse:
    memories = MemoryStore(db).list_memories(employee_id)
    return MemoryResponse(memories=memories)
