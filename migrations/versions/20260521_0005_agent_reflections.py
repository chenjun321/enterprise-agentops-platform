"""add agent reflection records

Revision ID: 20260521_0005
Revises: 20260521_0004
Create Date: 2026-05-21 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0005"
down_revision: Union[str, None] = "20260521_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_reflections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("employee_id", sa.String(length=160), nullable=False),
        sa.Column("target_agent", sa.String(length=80), nullable=False),
        sa.Column("intent", sa.String(length=120), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=False),
        sa.Column("rewrite_required", sa.Boolean(), nullable=False),
        sa.Column("checks", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_reflections_created_at"), "agent_reflections", ["created_at"], unique=False)
    op.create_index(op.f("ix_agent_reflections_employee_id"), "agent_reflections", ["employee_id"], unique=False)
    op.create_index(op.f("ix_agent_reflections_intent"), "agent_reflections", ["intent"], unique=False)
    op.create_index(op.f("ix_agent_reflections_passed"), "agent_reflections", ["passed"], unique=False)
    op.create_index(op.f("ix_agent_reflections_risk_level"), "agent_reflections", ["risk_level"], unique=False)
    op.create_index(op.f("ix_agent_reflections_session_id"), "agent_reflections", ["session_id"], unique=False)
    op.create_index(op.f("ix_agent_reflections_target_agent"), "agent_reflections", ["target_agent"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_reflections_target_agent"), table_name="agent_reflections")
    op.drop_index(op.f("ix_agent_reflections_session_id"), table_name="agent_reflections")
    op.drop_index(op.f("ix_agent_reflections_risk_level"), table_name="agent_reflections")
    op.drop_index(op.f("ix_agent_reflections_passed"), table_name="agent_reflections")
    op.drop_index(op.f("ix_agent_reflections_intent"), table_name="agent_reflections")
    op.drop_index(op.f("ix_agent_reflections_employee_id"), table_name="agent_reflections")
    op.drop_index(op.f("ix_agent_reflections_created_at"), table_name="agent_reflections")
    op.drop_table("agent_reflections")
