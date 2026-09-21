"""create conversations table and link conversation_messages

Revision ID: a3b4c5d6e7f8
Revises: f1a2b3c4d5e6
Create Date: 2026-09-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing messages predate the conversations table, so start clean before
    # enforcing the new foreign key.
    op.execute("DELETE FROM conversation_messages")

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversations_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_conversations_user_id", "conversations", ["user_id"], unique=False
    )
    op.create_index(
        "ix_conversations_created_at", "conversations", ["created_at"], unique=False
    )

    with op.batch_alter_table("conversation_messages") as batch_op:
        batch_op.create_foreign_key(
            "fk_conversation_messages_conversation_id_conversations",
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("conversation_messages") as batch_op:
        batch_op.drop_constraint(
            "fk_conversation_messages_conversation_id_conversations",
            type_="foreignkey",
        )

    op.drop_index("ix_conversations_created_at", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
