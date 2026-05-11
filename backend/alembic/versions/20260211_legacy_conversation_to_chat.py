"""Migrer conversation + message vers chat (messages_json) et renommer les FK.

PostgreSQL uniquement (agrégation JSON). Si la table « conversation » n’existe pas,
la migration ne fait rien (base déjà au nouveau schéma ou vierge gérée par init_db).

Revision ID: 20260211_legacy_to_chat
Revises:
Create Date: 2026-02-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "20260211_legacy_to_chat"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fk_name(bind, table: str, column: str) -> str | None:
    row = bind.execute(
        text(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_schema = kcu.constraint_schema
             AND tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = :tbl
              AND kcu.column_name = :col
              AND tc.constraint_type = 'FOREIGN KEY'
            LIMIT 1
            """
        ),
        {"tbl": table, "col": column},
    ).fetchone()
    return row[0] if row else None


def _drop_fk(bind, table: str, column: str) -> None:
    name = _fk_name(bind, table, column)
    if name:
        op.execute(text(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"'))


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if bind.dialect.name != "postgresql":
        if insp.has_table("conversation"):
            raise RuntimeError(
                "Cette migration ne gère que PostgreSQL (agrégation JSON). "
                "Pour un ancien schéma sous SQLite, exportez les données ou recréez la base.",
            )
        return

    if not insp.has_table("conversation"):
        return

    if insp.has_table("chat"):
        n = bind.execute(text("SELECT COUNT(*) FROM chat")).scalar()
        if int(n or 0) > 0:
            raise RuntimeError(
                "La table « chat » contient déjà des données alors que « conversation » "
                "existe encore. Sauvegardez la base, videz « chat », puis relancez la migration."
            )
        op.drop_table("chat")

    op.create_table(
        "chat",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default="Discussion"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("messages_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
    )

    op.execute(
        text(
            """
            INSERT INTO chat (id, user_id, title, created_at, updated_at, messages_json)
            SELECT
                c.id,
                c.user_id,
                c.title,
                c.created_at,
                c.updated_at,
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'id', m.id,
                                'role', m.role,
                                'content', m.content,
                                'created_at', to_char(
                                    m.created_at AT TIME ZONE 'UTC',
                                    'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'
                                )
                            )
                            ORDER BY m.created_at
                        )
                        FROM message m
                        WHERE m.conversation_id = c.id
                    ),
                    '[]'::json
                )
            FROM conversation c
            """
        )
    )

    seq = bind.execute(text("SELECT pg_get_serial_sequence('chat', 'id')")).scalar()
    if seq:
        # seq est du type public.chat_id_seq — provient du catalogue PostgreSQL
        bind.execute(
            text(
                f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM chat), 1))",
            ),
        )

    if insp.has_table("article"):
        cols = {c["name"] for c in insp.get_columns("article")}
        if "conversation_id" in cols and "chat_id" not in cols:
            op.add_column("article", sa.Column("chat_id", sa.Integer(), nullable=True))
            op.execute(text("UPDATE article SET chat_id = conversation_id"))
            _drop_fk(bind, "article", "conversation_id")
            op.drop_column("article", "conversation_id")
            op.alter_column("article", "chat_id", nullable=False)
            op.create_foreign_key(
                "article_chat_id_fkey",
                "article",
                "chat",
                ["chat_id"],
                ["id"],
            )

    if insp.has_table("pressreview"):
        cols = {c["name"] for c in insp.get_columns("pressreview")}
        if "conversation_id" in cols and "chat_id" not in cols:
            op.add_column("pressreview", sa.Column("chat_id", sa.Integer(), nullable=True))
            op.execute(text("UPDATE pressreview SET chat_id = conversation_id"))
            _drop_fk(bind, "pressreview", "conversation_id")
            op.drop_column("pressreview", "conversation_id")
            op.alter_column("pressreview", "chat_id", nullable=False)
            op.create_foreign_key(
                "pressreview_chat_id_fkey",
                "pressreview",
                "chat",
                ["chat_id"],
                ["id"],
            )

    if insp.has_table("message"):
        op.drop_table("message")
    if insp.has_table("conversation"):
        op.drop_table("conversation")


def downgrade() -> None:
    raise NotImplementedError(
        "Retour arrière non pris en charge : restaurez une sauvegarde SQL prise avant la migration.",
    )
