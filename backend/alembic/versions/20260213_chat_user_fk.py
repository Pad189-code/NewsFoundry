"""Add user_id FK constraint to chat table on fresh databases.

On fresh databases, the chat table is created without the user_id FK constraint
because the user table doesn't exist yet. This migration adds the constraint
after both tables are guaranteed to exist, ensuring schema consistency between
fresh and legacy migration paths.

Revision ID: 20260213_chat_user_fk
Revises: 20260212_system_prompt
Create Date: 2026-02-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260213_chat_user_fk"
down_revision: Union[str, None] = "20260212_system_prompt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Only run when both tables exist (i.e. fresh-database path after user table
    # has been created). Legacy paths already have the constraint from the
    # inline ForeignKeyConstraint in 20260211_legacy_to_chat.
    if not insp.has_table("chat") or not insp.has_table("user"):
        return

    # Check if the FK constraint already exists to avoid errors on legacy paths.
    fks = insp.get_foreign_keys("chat")
    fk_exists = any(fk["name"] == "chat_user_id_fkey" for fk in fks)

    if not fk_exists:
        op.create_foreign_key(
            "chat_user_id_fkey",
            "chat",
            "user",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    op.drop_constraint("chat_user_id_fkey", "chat", type_="foreignkey")
