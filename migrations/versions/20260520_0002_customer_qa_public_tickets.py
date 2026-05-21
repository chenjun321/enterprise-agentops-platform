"""extend support tickets for public customer QA

Revision ID: 20260520_0002
Revises: 20260506_0001
Create Date: 2026-05-20 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0002"
down_revision: Union[str, None] = "20260506_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("support_tickets") as batch_op:
        batch_op.alter_column("customer_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("customer_user_id", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("contact", sa.String(length=160), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("channel", sa.String(length=40), nullable=False, server_default="web"))
        batch_op.add_column(sa.Column("severity", sa.String(length=40), nullable=False, server_default="normal"))
        batch_op.add_column(sa.Column("bug_type", sa.String(length=80), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("reproduction_steps", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("user_reply", sa.Text(), nullable=False, server_default=""))
        batch_op.create_index("ix_support_tickets_customer_user_id", ["customer_user_id"], unique=False)
        batch_op.create_index("ix_support_tickets_severity", ["severity"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("support_tickets") as batch_op:
        batch_op.drop_index("ix_support_tickets_severity")
        batch_op.drop_index("ix_support_tickets_customer_user_id")
        batch_op.drop_column("user_reply")
        batch_op.drop_column("reproduction_steps")
        batch_op.drop_column("bug_type")
        batch_op.drop_column("severity")
        batch_op.drop_column("channel")
        batch_op.drop_column("contact")
        batch_op.drop_column("customer_user_id")
        batch_op.alter_column("customer_id", existing_type=sa.Integer(), nullable=False)
