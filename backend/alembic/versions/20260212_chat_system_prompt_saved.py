"""Colonne chat.system_prompt_saved (prompt système figé par discussion).

Revision ID: 20260212_system_prompt
Revises: 20260211_legacy_to_chat
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260212_system_prompt"
down_revision: Union[str, None] = "20260211_legacy_to_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat",
        sa.Column("system_prompt_saved", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat", "system_prompt_saved")
