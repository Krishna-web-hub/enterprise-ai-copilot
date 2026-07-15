"""Add is_pinned and pin_order to chat_sessions

Revision ID: 004
Revises: 003
Create Date: 2025-07-11

Adds pin support for chat sessions. Users can pin up to 5 sessions
for quick access, with ordering support via pin_order.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("chat_sessions", sa.Column("pin_order", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("chat_sessions", "pin_order")
    op.drop_column("chat_sessions", "is_pinned")
