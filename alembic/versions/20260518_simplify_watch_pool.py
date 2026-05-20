"""simplify watch_pool: remove source_*/xueqiu_url/is_blacklist/blacklist_reason/lifecycle_status, rename pool_status→status

Revision ID: 20260518_simplify
Revises: 20260516_0020
Create Date: 2026-05-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260518_simplify"
down_revision: Union[str, None] = "20260516_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop indexes that reference pool_status or lifecycle_status
    op.drop_index("ix_watch_pool_code_status", table_name="watch_pool")
    op.drop_index("ix_watch_pool_code_lifecycle", table_name="watch_pool")

    # Drop columns
    with op.batch_alter_table("watch_pool") as batch:
        batch.drop_column("source_type")
        batch.drop_column("source_platform")
        batch.drop_column("source_rank")
        batch.drop_column("source_score")
        batch.drop_column("source_reason")
        batch.drop_column("xueqiu_url")
        batch.drop_column("is_blacklist")
        batch.drop_column("blacklist_reason")
        batch.drop_column("lifecycle_status")
        batch.alter_column("pool_status", new_column_name="status", existing_type=sa.String(32), existing_nullable=False)

    # Recreate index
    op.create_index("ix_watch_pool_code_status", "watch_pool", ["stock_code", "status"])


def downgrade() -> None:
    op.drop_index("ix_watch_pool_code_status", table_name="watch_pool")

    with op.batch_alter_table("watch_pool") as batch:
        batch.alter_column("status", new_column_name="pool_status", existing_type=sa.String(32), existing_nullable=False)
        batch.add_column(sa.Column("lifecycle_status", sa.String(32), nullable=False, server_default="watching"))
        batch.add_column(sa.Column("blacklist_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("is_blacklist", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("xueqiu_url", sa.String(512), nullable=True))
        batch.add_column(sa.Column("source_reason", sa.Text(), nullable=True, server_default=""))
        batch.add_column(sa.Column("source_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("source_rank", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_platform", sa.String(32), nullable=True))
        batch.add_column(sa.Column("source_type", sa.String(32), nullable=True))

    op.create_index("ix_watch_pool_code_status", "watch_pool", ["stock_code", "pool_status"])
    op.create_index("ix_watch_pool_code_lifecycle", "watch_pool", ["stock_code", "lifecycle_status"])
