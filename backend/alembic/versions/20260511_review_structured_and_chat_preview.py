"""Revue de presse structurée + aperçu sur Chat.

Revision ID: 20260511_review_structured
Revises: 20260212_system_prompt
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260511_review_structured"
down_revision: Union[str, None] = "20260212_system_prompt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("pressreview"):
        op.add_column(
            "pressreview",
            sa.Column("review_title", sa.String(), nullable=True),
        )
        op.add_column(
            "pressreview",
            sa.Column("general_summary", sa.Text(), nullable=True),
        )
        op.add_column(
            "pressreview",
            sa.Column("articles_breakdown_json", sa.JSON(), nullable=True),
        )

    op.add_column(
        "chat",
        sa.Column("review_display_title", sa.String(), nullable=True),
    )
    op.add_column(
        "chat",
        sa.Column("review_general_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat",
        sa.Column("review_articles_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    op.drop_column("chat", "review_articles_json")
    op.drop_column("chat", "review_general_summary")
    op.drop_column("chat", "review_display_title")

    if insp.has_table("pressreview"):
        op.drop_column("pressreview", "articles_breakdown_json")
        op.drop_column("pressreview", "general_summary")
        op.drop_column("pressreview", "review_title")
