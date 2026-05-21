import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConversationThread, PendingHumanInput, ThreadState


ORDER_RE = re.compile(r"\bO\d{8,}\b", re.IGNORECASE)
TRACE_RE = re.compile(r"\btrace[_\-a-zA-Z0-9]+\b", re.IGNORECASE)
WALLET_RE = re.compile(r"\b0x[a-fA-F0-9]{6,}\b")


QUESTION_TEMPLATES = {
    "order_no_or_trace_id": "请提供订单号或支付流水/trace_id，我才能继续核对订单和支付状态。",
    "campaign_name": "请提供活动名称，我才能继续分析活动数据。",
    "customer_name_or_company": "请提供客户姓名或公司名称，我才能继续查询客户画像。",
    "business_domain": "请说明这是营销、销售还是 QA 问题。",
}


class ThreadContextService:
    def __init__(self, db: Session):
        self.db = db

    def merge_context(self, thread_id: str, message: str, request_context: Dict[str, Any]) -> Dict[str, Any]:
        stored = self.get_state(thread_id)
        extracted = extract_state_from_text(message)
        merged = {**stored, **request_context, **{key: value for key, value in extracted.items() if value}}
        self.upsert_state(thread_id, merged)
        return merged

    def get_state(self, thread_id: str) -> Dict[str, Any]:
        row = self.db.get(ThreadState, thread_id)
        if not row:
            return {}
        return json.loads(row.state_json or "{}")

    def upsert_state(self, thread_id: str, state: Dict[str, Any]) -> None:
        existing = self.db.get(ThreadState, thread_id)
        payload = json.dumps(state, ensure_ascii=False, default=str)
        if existing:
            existing.state_json = payload
            existing.updated_at = datetime.utcnow()
        else:
            self.db.add(ThreadState(thread_id=thread_id, state_json=payload))
        self.db.flush()

    def open_pending_input(
        self,
        *,
        thread_id: str,
        target_agent: str,
        intent: str,
        missing_fields: List[str],
    ) -> PendingHumanInput:
        self.close_pending_inputs(thread_id)
        question = " ".join(QUESTION_TEMPLATES.get(field, f"请补充 {field}。") for field in missing_fields)
        pending = PendingHumanInput(
            thread_id=thread_id,
            target_agent=target_agent,
            intent=intent,
            missing_fields=json.dumps(missing_fields, ensure_ascii=False),
            question=question,
            status="open",
        )
        self.db.add(pending)
        thread = self.db.get(ConversationThread, thread_id)
        if thread:
            thread.status = "waiting_for_input"
            thread.updated_at = datetime.utcnow()
        self.db.flush()
        return pending

    def get_open_pending_input(self, thread_id: str) -> Optional[PendingHumanInput]:
        stmt = (
            select(PendingHumanInput)
            .where(PendingHumanInput.thread_id == thread_id, PendingHumanInput.status == "open")
            .order_by(PendingHumanInput.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def maybe_resume_pending_input(self, thread_id: str, context: Dict[str, Any]) -> Optional[PendingHumanInput]:
        pending = self.get_open_pending_input(thread_id)
        if not pending:
            return None
        missing_fields = json.loads(pending.missing_fields or "[]")
        if missing_fields_satisfied(missing_fields, context):
            pending.status = "resolved"
            pending.resolved_at = datetime.utcnow()
            thread = self.db.get(ConversationThread, thread_id)
            if thread:
                thread.status = "active"
                thread.updated_at = datetime.utcnow()
            self.db.flush()
            return pending
        return None

    def close_pending_inputs(self, thread_id: str) -> None:
        for pending in self.db.execute(
            select(PendingHumanInput).where(PendingHumanInput.thread_id == thread_id, PendingHumanInput.status == "open")
        ).scalars():
            pending.status = "closed"
            pending.resolved_at = datetime.utcnow()
        self.db.flush()


def extract_state_from_text(text: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    order = ORDER_RE.search(text)
    trace = TRACE_RE.search(text)
    wallet = WALLET_RE.search(text)
    if order:
        state["order_no"] = order.group(0).upper()
    if trace:
        state["trace_id"] = trace.group(0)
    if wallet:
        state["wallet_address"] = wallet.group(0)
    return state


def missing_fields_satisfied(missing_fields: List[str], context: Dict[str, Any]) -> bool:
    for field in missing_fields:
        if field == "order_no_or_trace_id" and not (context.get("order_no") or context.get("trace_id")):
            return False
        if field == "customer_name_or_company" and not (context.get("customer_name") or context.get("company")):
            return False
        if field not in {"order_no_or_trace_id", "customer_name_or_company"} and not context.get(field):
            return False
    return True
