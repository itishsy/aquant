"""PRD v1 clean baseline schema.

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op

from app.models import entities  # noqa: F401
from app.models.base import SystemBase


revision = "20260505_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    SystemBase.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    SystemBase.metadata.drop_all(bind=bind)
