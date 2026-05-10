"""initial production schema

Revision ID: 20260506_0001
Revises:
Create Date: 2026-05-06 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260506_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=False),
        sa.Column("industry", sa.String(length=80), nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=40), nullable=False),
        sa.Column("usage_level", sa.String(length=40), nullable=False),
        sa.Column("pain_points", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_company"), "customers", ["company"], unique=False)
    op.create_index(op.f("ix_customers_industry"), "customers", ["industry"], unique=False)
    op.create_index(op.f("ix_customers_name"), "customers", ["name"], unique=False)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.String(length=20), nullable=False),
        sa.Column("end_date", sa.String(length=20), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaigns_channel"), "campaigns", ["channel"], unique=False)
    op.create_index(op.f("ix_campaigns_name"), "campaigns", ["name"], unique=False)

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("doc_type", sa.String(length=80), nullable=False),
        sa.Column("permission_level", sa.String(length=80), nullable=False),
        sa.Column("source_path", sa.String(length=300), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_documents_doc_type"), "knowledge_documents", ["doc_type"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_domain"), "knowledge_documents", ["domain"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_title"), "knowledge_documents", ["title"], unique=False)

    op.create_table(
        "memory_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("memory_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("old_content", sa.Text(), nullable=False),
        sa.Column("new_content", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_events_employee_id"), "memory_events", ["employee_id"], unique=False)
    op.create_index(op.f("ix_memory_events_event_type"), "memory_events", ["event_type"], unique=False)

    op.create_table(
        "product_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("service", sa.String(length=80), nullable=False),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("order_no", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_logs_level"), "product_logs", ["level"], unique=False)
    op.create_index(op.f("ix_product_logs_order_no"), "product_logs", ["order_no"], unique=False)
    op.create_index(op.f("ix_product_logs_service"), "product_logs", ["service"], unique=False)
    op.create_index(op.f("ix_product_logs_timestamp"), "product_logs", ["timestamp"], unique=False)
    op.create_index(op.f("ix_product_logs_trace_id"), "product_logs", ["trace_id"], unique=False)
    op.create_index(op.f("ix_product_logs_user_id"), "product_logs", ["user_id"], unique=False)

    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(length=80), nullable=False),
        sa.Column("memory_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_memories_employee_id"), "user_memories", ["employee_id"], unique=False)
    op.create_index(op.f("ix_user_memories_memory_type"), "user_memories", ["memory_type"], unique=False)
    op.create_index(op.f("ix_user_memories_status"), "user_memories", ["status"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("employee_id", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_employee_id"), "audit_events", ["employee_id"], unique=False)
    op.create_index(op.f("ix_audit_events_event_type"), "audit_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_events_session_id"), "audit_events", ["session_id"], unique=False)

    op.create_table(
        "campaign_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("new_users", sa.Integer(), nullable=False),
        sa.Column("active_users", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("gmv", sa.Float(), nullable=False),
        sa.Column("day7_retained_users", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaign_events_channel"), "campaign_events", ["channel"], unique=False)
    op.create_index(op.f("ix_campaign_events_event_date"), "campaign_events", ["event_date"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_no", sa.String(length=80), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no"),
    )
    op.create_index(op.f("ix_orders_order_no"), "orders", ["order_no"], unique=True)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_trace_id"), "orders", ["trace_id"], unique=False)

    op.create_table(
        "sales_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_no", sa.String(length=80), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_no"),
    )
    op.create_index(op.f("ix_support_tickets_category"), "support_tickets", ["category"], unique=False)
    op.create_index(op.f("ix_support_tickets_ticket_no"), "support_tickets", ["ticket_no"], unique=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("provider_trade_no", sa.String(length=120), nullable=False),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("callback_received", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(op.f("ix_payments_trace_id"), "payments", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_trace_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_support_tickets_ticket_no"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_category"), table_name="support_tickets")
    op.drop_table("support_tickets")
    op.drop_table("sales_notes")
    op.drop_index(op.f("ix_orders_trace_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_order_no"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_campaign_events_event_date"), table_name="campaign_events")
    op.drop_index(op.f("ix_campaign_events_channel"), table_name="campaign_events")
    op.drop_table("campaign_events")
    op.drop_index(op.f("ix_audit_events_session_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_event_type"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_employee_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_user_memories_status"), table_name="user_memories")
    op.drop_index(op.f("ix_user_memories_memory_type"), table_name="user_memories")
    op.drop_index(op.f("ix_user_memories_employee_id"), table_name="user_memories")
    op.drop_table("user_memories")
    op.drop_index(op.f("ix_product_logs_user_id"), table_name="product_logs")
    op.drop_index(op.f("ix_product_logs_trace_id"), table_name="product_logs")
    op.drop_index(op.f("ix_product_logs_timestamp"), table_name="product_logs")
    op.drop_index(op.f("ix_product_logs_service"), table_name="product_logs")
    op.drop_index(op.f("ix_product_logs_order_no"), table_name="product_logs")
    op.drop_index(op.f("ix_product_logs_level"), table_name="product_logs")
    op.drop_table("product_logs")
    op.drop_index(op.f("ix_memory_events_event_type"), table_name="memory_events")
    op.drop_index(op.f("ix_memory_events_employee_id"), table_name="memory_events")
    op.drop_table("memory_events")
    op.drop_index(op.f("ix_knowledge_documents_title"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_domain"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_doc_type"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    op.drop_index(op.f("ix_campaigns_name"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_channel"), table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index(op.f("ix_customers_name"), table_name="customers")
    op.drop_index(op.f("ix_customers_industry"), table_name="customers")
    op.drop_index(op.f("ix_customers_company"), table_name="customers")
    op.drop_table("customers")

