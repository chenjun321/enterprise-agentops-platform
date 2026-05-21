"""add thread state and pending human input

Revision ID: 20260521_0006
Revises: 20260521_0005
Create Date: 2026-05-21 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0006"
down_revision: Union[str, None] = "20260521_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "thread_states",
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"]),
        sa.PrimaryKeyConstraint("thread_id"),
    )
    op.create_index(op.f("ix_thread_states_updated_at"), "thread_states", ["updated_at"], unique=False)

    op.create_table(
        "pending_human_inputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("intent", sa.String(length=120), nullable=False),
        sa.Column("target_agent", sa.String(length=80), nullable=False),
        sa.Column("missing_fields", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pending_human_inputs_created_at"), "pending_human_inputs", ["created_at"], unique=False)
    op.create_index(op.f("ix_pending_human_inputs_intent"), "pending_human_inputs", ["intent"], unique=False)
    op.create_index(op.f("ix_pending_human_inputs_status"), "pending_human_inputs", ["status"], unique=False)
    op.create_index(op.f("ix_pending_human_inputs_target_agent"), "pending_human_inputs", ["target_agent"], unique=False)
    op.create_index(op.f("ix_pending_human_inputs_thread_id"), "pending_human_inputs", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pending_human_inputs_thread_id"), table_name="pending_human_inputs")
    op.drop_index(op.f("ix_pending_human_inputs_target_agent"), table_name="pending_human_inputs")
    op.drop_index(op.f("ix_pending_human_inputs_status"), table_name="pending_human_inputs")
    op.drop_index(op.f("ix_pending_human_inputs_intent"), table_name="pending_human_inputs")
    op.drop_index(op.f("ix_pending_human_inputs_created_at"), table_name="pending_human_inputs")
    op.drop_table("pending_human_inputs")
    op.drop_index(op.f("ix_thread_states_updated_at"), table_name="thread_states")
    op.drop_table("thread_states")
