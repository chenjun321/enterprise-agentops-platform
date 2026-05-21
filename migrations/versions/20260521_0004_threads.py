"""add persistent threads and db locks

Revision ID: 20260521_0004
Revises: 20260520_0003
Create Date: 2026-05-21 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0004"
down_revision: Union[str, None] = "20260520_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_threads",
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id"),
    )
    op.create_index(op.f("ix_conversation_threads_actor_id"), "conversation_threads", ["actor_id"], unique=False)
    op.create_index(op.f("ix_conversation_threads_actor_type"), "conversation_threads", ["actor_type"], unique=False)
    op.create_index(op.f("ix_conversation_threads_channel"), "conversation_threads", ["channel"], unique=False)
    op.create_index(op.f("ix_conversation_threads_created_at"), "conversation_threads", ["created_at"], unique=False)
    op.create_index(op.f("ix_conversation_threads_status"), "conversation_threads", ["status"], unique=False)
    op.create_index(op.f("ix_conversation_threads_updated_at"), "conversation_threads", ["updated_at"], unique=False)

    op.create_table(
        "thread_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_thread_messages_created_at"), "thread_messages", ["created_at"], unique=False)
    op.create_index(op.f("ix_thread_messages_role"), "thread_messages", ["role"], unique=False)
    op.create_index(op.f("ix_thread_messages_thread_id"), "thread_messages", ["thread_id"], unique=False)

    op.create_table(
        "thread_locks",
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("thread_id"),
    )
    op.create_index(op.f("ix_thread_locks_expires_at"), "thread_locks", ["expires_at"], unique=False)
    op.create_index(op.f("ix_thread_locks_owner_id"), "thread_locks", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_thread_locks_owner_id"), table_name="thread_locks")
    op.drop_index(op.f("ix_thread_locks_expires_at"), table_name="thread_locks")
    op.drop_table("thread_locks")
    op.drop_index(op.f("ix_thread_messages_thread_id"), table_name="thread_messages")
    op.drop_index(op.f("ix_thread_messages_role"), table_name="thread_messages")
    op.drop_index(op.f("ix_thread_messages_created_at"), table_name="thread_messages")
    op.drop_table("thread_messages")
    op.drop_index(op.f("ix_conversation_threads_updated_at"), table_name="conversation_threads")
    op.drop_index(op.f("ix_conversation_threads_status"), table_name="conversation_threads")
    op.drop_index(op.f("ix_conversation_threads_created_at"), table_name="conversation_threads")
    op.drop_index(op.f("ix_conversation_threads_channel"), table_name="conversation_threads")
    op.drop_index(op.f("ix_conversation_threads_actor_type"), table_name="conversation_threads")
    op.drop_index(op.f("ix_conversation_threads_actor_id"), table_name="conversation_threads")
    op.drop_table("conversation_threads")
