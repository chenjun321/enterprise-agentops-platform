"""add usage events for token budget guard

Revision ID: 20260520_0003
Revises: 20260520_0002
Create Date: 2026-05-20 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0003"
down_revision: Union[str, None] = "20260520_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("route", sa.String(length=120), nullable=False),
        sa.Column("ip_address", sa.String(length=80), nullable=False),
        sa.Column("message_hash", sa.String(length=80), nullable=False),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_output_tokens", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_events_actor_id"), "usage_events", ["actor_id"], unique=False)
    op.create_index(op.f("ix_usage_events_actor_type"), "usage_events", ["actor_type"], unique=False)
    op.create_index(op.f("ix_usage_events_created_at"), "usage_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_usage_events_ip_address"), "usage_events", ["ip_address"], unique=False)
    op.create_index(op.f("ix_usage_events_message_hash"), "usage_events", ["message_hash"], unique=False)
    op.create_index(op.f("ix_usage_events_route"), "usage_events", ["route"], unique=False)
    op.create_index(op.f("ix_usage_events_status"), "usage_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_status"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_route"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_message_hash"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_ip_address"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_created_at"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_actor_type"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_actor_id"), table_name="usage_events")
    op.drop_table("usage_events")
