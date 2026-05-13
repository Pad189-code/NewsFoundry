"""Chat.loaded_articles (URLs des articles chargés).

Revision ID: 20260513_loaded_articles
Revises: 20260511_review_structured
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260513_loaded_articles"
down_revision: Union[str, None] = "20260511_review_structured"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat",
        sa.Column("loaded_articles", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat", "loaded_articles")
