"""create conversation_messages table

Revision ID: 8f1c2d3e4a5b
Revises: 2a0dbe8e4d28
Create Date: 2026-09-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1c2d3e4a5b"
down_revision: str | None = "2a0dbe8e4d28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id",
        "conversation_messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_messages_user_id",
        "conversation_messages",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_messages_role",
        "conversation_messages",
        ["role"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_messages_created_at",
        "conversation_messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_messages_created_at", table_name="conversation_messages"
    )
    op.drop_index("ix_conversation_messages_role", table_name="conversation_messages")
    op.drop_index(
        "ix_conversation_messages_user_id", table_name="conversation_messages"
    )
    op.drop_index(
        "ix_conversation_messages_conversation_id",
        table_name="conversation_messages",
    )
    op.drop_table("conversation_messages")
