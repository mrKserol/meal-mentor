"""add ai chat message pagination index"""

from alembic import op

revision = "025_add_ai_chat_message_pagination_index"
down_revision = "024_create_ai_chat_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_ai_chat_messages_thread_id_id",
        "ai_chat_messages",
        ["thread_id", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_chat_messages_thread_id_id", table_name="ai_chat_messages")
