"""add watch auto remove price

Revision ID: 20260521_auto_remove
Revises: 20260518_simplify
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_auto_remove"
down_revision: Union[str, None] = "20260518_simplify"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("watch_pool") as batch:
        batch.add_column(sa.Column("auto_remove_price", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("watch_pool") as batch:
        batch.drop_column("auto_remove_price")
