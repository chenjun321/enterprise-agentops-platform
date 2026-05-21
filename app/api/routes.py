from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.core.config import get_settings
from app.core.state import AgentState
from app.db.database import get_db
from app.memory.store import MemoryStore
from app.schemas.api import (
    ChatRequest,
    ChatResponse,
    CustomerQARequest,
    CustomerQAResponse,
    MeResponse,
    MemoryCreateRequest,
    MemoryResponse,
)
from app.security.auth import (
    AuthContext,
    get_optional_auth_context,
    require_internal_api_key,
    require_public_channel_token,
)
from app.services.usage_guard import UsageGuard
from app.services.thread_store import ThreadBusyError, ThreadStore
from app.services.thread_context import ThreadContextService


internal_router = APIRouter(dependencies=[Depends(require_internal_api_key)])
public_router = APIRouter(dependencies=[Depends(require_public_channel_token)])
router = internal_router


def _build_chat_response(state: AgentState) -> ChatResponse:
    settings = get_settings()
    expose_internal = settings.expose_internal_traces
    return ChatResponse(
        session_id=state.session_id,
        thread_id=state.session_id,
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


@internal_router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> ChatResponse:
    employee_id, role, _ = _resolve_identity(request.employee_id, request.role, auth)
    thread_store = ThreadStore(db)
    thread_id = thread_store.resolve_thread_id(request.thread_id or request.session_id)
    _enforce_usage_guard(
        db=db,
        actor_id=employee_id,
        actor_type=role,
        route="/api/chat",
        ip_address=_client_ip(http_request),
        message=request.message,
        context=request.context,
    )
    owner_id = f"pod_request:{getattr(http_request.state, 'request_id', uuid4().hex)}"
    try:
        with thread_store.lock(thread_id, owner_id):
            thread_context = ThreadContextService(db)
            thread_store.ensure_thread(thread_id=thread_id, actor_id=employee_id, actor_type=role, channel="internal")
            context = thread_context.merge_context(thread_id, request.message, dict(request.context))
            resumed = thread_context.maybe_resume_pending_input(thread_id, context)
            if resumed:
                context["_resume_intent"] = resumed.intent
                context["_resume_target_agent"] = resumed.target_agent
            context["_thread_history"] = thread_store.recent_messages(thread_id)
            thread_store.append_message(thread_id=thread_id, role="user", content=request.message, payload={"context": request.context})
            state = AgentState(
                session_id=thread_id,
                employee_id=employee_id,
                role=role,
                message=request.message,
                context=context,
            )
            orchestrator = AgentOrchestrator(db)
            state = orchestrator.run(state)
            thread_store.append_message(
                thread_id=thread_id,
                role="assistant",
                content=(state.final_response or {}).get("user_reply") or str(state.final_response or {}),
                payload={"answer": state.final_response, "target_agent": state.target_agent, "intent": state.intent},
            )
            db.commit()
            return _build_chat_response(state)
    except ThreadBusyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "thread_busy", "thread_id": thread_id})


@public_router.post("/customer/qa", response_model=CustomerQAResponse)
def customer_qa(
    request: CustomerQARequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> CustomerQAResponse:
    customer_user_id = request.customer_user_id or request.context.get("customer_user_id") or "anonymous"
    thread_store = ThreadStore(db)
    thread_id = thread_store.resolve_thread_id(request.thread_id or request.session_id)
    context = dict(request.context)
    context.update(
        {
            "customer_user_id": customer_user_id,
            "contact": request.contact or context.get("contact", ""),
            "channel": request.channel,
            "public_entrypoint": True,
        }
    )
    _enforce_usage_guard(
        db=db,
        actor_id=f"customer:{customer_user_id}",
        actor_type="customer",
        route="/api/customer/qa",
        ip_address=_client_ip(http_request),
        message=request.message,
        context=context,
    )
    owner_id = f"pod_request:{getattr(http_request.state, 'request_id', uuid4().hex)}"
    try:
        with thread_store.lock(thread_id, owner_id):
            thread_context = ThreadContextService(db)
            actor_id = f"customer:{customer_user_id}"
            thread_store.ensure_thread(thread_id=thread_id, actor_id=actor_id, actor_type="customer", channel=request.channel)
            context = thread_context.merge_context(thread_id, request.message, context)
            resumed = thread_context.maybe_resume_pending_input(thread_id, context)
            if resumed:
                context["_resume_intent"] = resumed.intent
                context["_resume_target_agent"] = resumed.target_agent
            context["_thread_history"] = thread_store.recent_messages(thread_id)
            thread_store.append_message(thread_id=thread_id, role="user", content=request.message, payload={"context": request.context})
            state = AgentState(
                session_id=thread_id,
                employee_id=actor_id,
                role="customer",
                message=request.message,
                context=context,
            )
            orchestrator = AgentOrchestrator(db)
            state = orchestrator.run(state)
            thread_store.append_message(
                thread_id=thread_id,
                role="assistant",
                content=(state.final_response or {}).get("user_reply") or str(state.final_response or {}),
                payload={"answer": state.final_response, "intent": state.intent},
            )
            db.commit()
    except ThreadBusyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "thread_busy", "thread_id": thread_id})
    answer = state.final_response or {}
    ticket = answer.get("ticket")
    public_answer = {
        "answer_type": answer.get("answer_type", "qa_response"),
        "user_reply": answer.get("user_reply") or answer.get("message") or "我们已收到你的问题，会尽快处理。",
        "steps": answer.get("steps", []),
        "next_action": answer.get("next_action", ""),
        "confidence": answer.get("confidence", 0),
    }
    return CustomerQAResponse(
        session_id=state.session_id,
        thread_id=state.session_id,
        intent=state.intent,
        answer=public_answer,
        ticket=ticket,
    )


@internal_router.post("/memory", response_model=MemoryResponse)
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


@internal_router.get("/memory/{employee_id}", response_model=MemoryResponse)
def list_memory(
    employee_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> MemoryResponse:
    actor_employee_id, actor_role = _resolve_memory_actor_scope(employee_id, auth)
    _assert_memory_access(actor_employee_id, actor_role, employee_id)
    memories = MemoryStore(db).list_memories(employee_id)
    return MemoryResponse(memories=memories)


@internal_router.get("/me", response_model=MeResponse)
def me(auth: Optional[AuthContext] = Depends(get_optional_auth_context)) -> MeResponse:
    employee_id, role, auth_mode = _resolve_identity(None, None, auth)
    return MeResponse(employee_id=employee_id, role=role, auth_mode=auth_mode)


def _enforce_usage_guard(
    *,
    db: Session,
    actor_id: str,
    actor_type: str,
    route: str,
    ip_address: str,
    message: str,
    context: dict,
) -> None:
    decision = UsageGuard(db).check_and_record(
        actor_id=actor_id,
        actor_type=actor_type,
        route=route,
        ip_address=ip_address,
        message=message,
        context=context,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "usage_limit_exceeded",
                "reason": decision.reason,
                "estimated_input_tokens": decision.estimated_input_tokens,
                "remaining_day_tokens": decision.remaining_day_tokens,
            },
        )


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
