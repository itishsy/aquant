"""init mvp

Revision ID: 20260426_0001
Revises:
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260426_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.base import SystemBase
    from app.models import entities  # noqa: F401

    bind = op.get_bind()
    SystemBase.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=bind)
    meta.drop_all(bind=bind)
