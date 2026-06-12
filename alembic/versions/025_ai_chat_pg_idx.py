"""add ai chat message pagination index"""

from alembic import op

revision = "025_ai_chat_pg_idx"
down_revision = "024_create_ai_chat_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ai_chat_messages_thread_id_id
        ON ai_chat_messages(thread_id, id)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_ai_chat_messages_thread_id_id
        """
    )
