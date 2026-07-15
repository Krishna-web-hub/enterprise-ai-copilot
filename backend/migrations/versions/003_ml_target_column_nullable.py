"""Make ml_models.target_column nullable (unsupervised tasks have no target)

Revision ID: 003
Revises: 002
Create Date: 2025-01-25

Clustering and anomaly detection are unsupervised — they have no target
label, so target_column must be nullable to support them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("ml_models", "target_column", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("ml_models", "target_column", existing_type=sa.String(255), nullable=False)
