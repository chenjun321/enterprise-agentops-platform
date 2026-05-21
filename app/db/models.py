from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    company: Mapped[str] = mapped_column(String(160), index=True)
    industry: Mapped[str] = mapped_column(String(80), index=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(40), default="prospect")
    usage_level: Mapped[str] = mapped_column(String(40), default="unknown")
    pain_points: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")


class SalesNote(Base):
    __tablename__ = "sales_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    note: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), index=True)
    trace_id: Mapped[str] = mapped_column(String(120), index=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    payment = relationship("Payment", back_populates="order", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    provider: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), index=True)
    provider_trade_no: Mapped[str] = mapped_column(String(120), default="")
    trace_id: Mapped[str] = mapped_column(String(120), index=True, default="")
    callback_received: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="payment")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    channel: Mapped[str] = mapped_column(String(80), index=True)
    start_date: Mapped[str] = mapped_column(String(20))
    end_date: Mapped[str] = mapped_column(String(20))
    goal: Mapped[str] = mapped_column(Text, default="")


class CampaignEvent(Base):
    __tablename__ = "campaign_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    event_date: Mapped[str] = mapped_column(String(20), index=True)
    channel: Mapped[str] = mapped_column(String(80), index=True)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    gmv: Mapped[float] = mapped_column(Float, default=0.0)
    day7_retained_users: Mapped[int] = mapped_column(Integer, default=0)


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    customer_user_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    contact: Mapped[str] = mapped_column(String(160), default="")
    channel: Mapped[str] = mapped_column(String(40), default="web")
    category: Mapped[str] = mapped_column(String(80), index=True)
    question: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    bug_type: Mapped[str] = mapped_column(String(80), default="")
    reproduction_steps: Mapped[str] = mapped_column(Text, default="")
    user_reply: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductLog(Base):
    __tablename__ = "product_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    level: Mapped[str] = mapped_column(String(20), index=True)
    service: Mapped[str] = mapped_column(String(80), index=True)
    trace_id: Mapped[str] = mapped_column(String(120), index=True)
    user_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    order_no: Mapped[str] = mapped_column(String(80), index=True, default="")
    message: Mapped[str] = mapped_column(Text)


class UserMemory(Base):
    __tablename__ = "user_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(80), index=True)
    memory_type: Mapped[str] = mapped_column(String(80), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class MemoryEvent(Base):
    __tablename__ = "memory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memory_id: Mapped[int] = mapped_column(Integer, nullable=True)
    employee_id: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    old_content: Mapped[str] = mapped_column(Text, default="")
    new_content: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(120), index=True)
    employee_id: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentReflection(Base):
    __tablename__ = "agent_reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(120), index=True)
    employee_id: Mapped[str] = mapped_column(String(160), index=True)
    target_agent: Mapped[str] = mapped_column(String(80), index=True)
    intent: Mapped[str] = mapped_column(String(120), index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    risk_level: Mapped[str] = mapped_column(String(40), default="low", index=True)
    rewrite_required: Mapped[bool] = mapped_column(Boolean, default=False)
    checks: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(160), index=True)
    actor_type: Mapped[str] = mapped_column(String(40), index=True)
    route: Mapped[str] = mapped_column(String(120), index=True)
    ip_address: Mapped[str] = mapped_column(String(80), index=True, default="")
    message_hash: Mapped[str] = mapped_column(String(80), index=True)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), index=True, default="accepted")
    reason: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    thread_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(160), index=True)
    actor_type: Mapped[str] = mapped_column(String(40), index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True, default="internal")
    status: Mapped[str] = mapped_column(String(40), index=True, default="active")
    summary: Mapped[str] = mapped_column(Text, default="")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ThreadMessage(Base):
    __tablename__ = "thread_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("conversation_threads.thread_id"), index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    content: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ThreadLock(Base):
    __tablename__ = "thread_locks"

    thread_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(120), index=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class ThreadState(Base):
    __tablename__ = "thread_states"

    thread_id: Mapped[str] = mapped_column(ForeignKey("conversation_threads.thread_id"), primary_key=True)
    state_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PendingHumanInput(Base):
    __tablename__ = "pending_human_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("conversation_threads.thread_id"), index=True)
    intent: Mapped[str] = mapped_column(String(120), index=True)
    target_agent: Mapped[str] = mapped_column(String(80), index=True)
    missing_fields: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    domain: Mapped[str] = mapped_column(String(80), index=True)
    doc_type: Mapped[str] = mapped_column(String(80), index=True)
    permission_level: Mapped[str] = mapped_column(String(80), default="employee")
    source_path: Mapped[str] = mapped_column(String(300))
    version: Mapped[str] = mapped_column(String(40), default="v1")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
