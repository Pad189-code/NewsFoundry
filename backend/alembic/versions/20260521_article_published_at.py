"""Article.published_at (date de publication presse).

Revision ID: 20260521_published_at
Revises: 20260513_loaded_articles
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260521_published_at"
down_revision: Union[str, None] = "20260513_loaded_articles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # article table only exists in legacy databases, not in fresh installations.
    # Skip these operations on fresh databases to avoid "relation does not exist" errors.
    if insp.has_table("article"):
        op.add_column(
            "article",
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_article_published_at", "article", ["published_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # article table only exists in legacy databases, not in fresh installations.
    # Skip these operations on fresh databases to avoid "relation does not exist" errors.
    if insp.has_table("article"):
        op.drop_index("ix_article_published_at", table_name="article")
        op.drop_column("article", "published_at")
