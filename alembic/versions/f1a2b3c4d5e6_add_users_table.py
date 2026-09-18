"""add users table and user foreign keys

Revision ID: f1a2b3c4d5e6
Revises: 8f1c2d3e4a5b
Create Date: 2026-09-19 02:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "8f1c2d3e4a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.create_foreign_key(
            "fk_user_preferences_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("conversation_messages") as batch_op:
        batch_op.create_foreign_key(
            "fk_conversation_messages_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("conversation_messages") as batch_op:
        batch_op.drop_constraint(
            "fk_conversation_messages_user_id_users", type_="foreignkey"
        )

    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.drop_constraint(
            "fk_user_preferences_user_id_users", type_="foreignkey"
        )

    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
