from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.core.config import get_settings
from app.core.state import AgentState
from app.db.database import get_db
from app.memory.store import MemoryStore
from app.schemas.api import ChatRequest, ChatResponse, MeResponse, MemoryCreateRequest, MemoryResponse
from app.security.auth import AuthContext, get_optional_auth_context, require_internal_api_key


router = APIRouter(dependencies=[Depends(require_internal_api_key)])


def _build_chat_response(state: AgentState) -> ChatResponse:
    settings = get_settings()
    expose_internal = settings.expose_internal_traces
    return ChatResponse(
        session_id=state.session_id,
        target_agent=state.target_agent,
        intent=state.intent,
        answer=state.final_response or {},
        evidence=state.evidence if expose_internal else [],
        plan=state.plan.model_dump() if state.plan and expose_internal else {},
        audit_events=[item.model_dump() for item in state.audit_events] if expose_internal else [],
    )


def _resolve_identity(
    request_employee_id: Optional[str],
    request_role: Optional[str],
    auth: Optional[AuthContext],
) -> tuple[str, str, str]:
    if auth:
        if request_employee_id and request_employee_id != auth.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="employee_id_mismatch")
        if request_role and request_role != auth.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role_mismatch")
        return auth.employee_id, auth.role, "token"

    if not request_employee_id or not request_role:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employee_id and role are required when bearer auth is disabled",
        )
    return request_employee_id, request_role, "body"


def _assert_memory_access(actor_employee_id: str, actor_role: str, target_employee_id: str) -> None:
    if actor_role == "admin":
        return
    if actor_employee_id != target_employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="memory_access_denied")


def _resolve_memory_actor_scope(
    request_employee_id: Optional[str],
    auth: Optional[AuthContext],
) -> tuple[str, str]:
    if auth:
        if request_employee_id and request_employee_id != auth.employee_id and auth.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="employee_id_mismatch")
        return request_employee_id or auth.employee_id, auth.role

    if not request_employee_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employee_id is required when bearer auth is disabled",
        )
    return request_employee_id, "self"


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> ChatResponse:
    employee_id, role, _ = _resolve_identity(request.employee_id, request.role, auth)
    initial = AgentState(employee_id=employee_id, role=role, message=request.message)
    state = AgentState(
        session_id=request.session_id or initial.session_id,
        employee_id=employee_id,
        role=role,
        message=request.message,
        context=request.context,
    )
    orchestrator = AgentOrchestrator(db)
    state = orchestrator.run(state)
    return _build_chat_response(state)


@router.post("/memory", response_model=MemoryResponse)
def create_memory(
    request: MemoryCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> MemoryResponse:
    employee_id, role = _resolve_memory_actor_scope(request.employee_id, auth)
    _assert_memory_access(employee_id, role, employee_id)
    memory = MemoryStore(db).create_memory(
        employee_id=employee_id,
        memory_type=request.memory_type,
        content=request.content,
        source=request.source,
    )
    return MemoryResponse(memories=[memory])


@router.get("/memory/{employee_id}", response_model=MemoryResponse)
def list_memory(
    employee_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> MemoryResponse:
    actor_employee_id, actor_role = _resolve_memory_actor_scope(employee_id, auth)
    _assert_memory_access(actor_employee_id, actor_role, employee_id)
    memories = MemoryStore(db).list_memories(employee_id)
    return MemoryResponse(memories=memories)


@router.get("/me", response_model=MeResponse)
def me(auth: Optional[AuthContext] = Depends(get_optional_auth_context)) -> MeResponse:
    employee_id, role, auth_mode = _resolve_identity(None, None, auth)
    return MeResponse(employee_id=employee_id, role=role, auth_mode=auth_mode)
