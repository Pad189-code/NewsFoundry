"""Merge chat_user_fk and review_structured heads.

This merge migration resolves the multiple-head situation created when
20260213_chat_user_fk and 20260511_review_structured were both created
with down_revision pointing to 20260212_system_prompt. They operate on
independent schema changes and can run in any order, so this merge
establishes a single head for future migrations.

Revision ID: 20260514_merge_heads
Revises: 20260213_chat_user_fk, 20260511_review_structured
Create Date: 2026-05-14
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260514_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("20260213_chat_user_fk", "20260511_review_structured")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge migration — no schema changes
    pass


def downgrade() -> None:
    # Merge migration — no schema changes
    pass
