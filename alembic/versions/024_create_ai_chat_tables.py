"""create ai chat tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024_create_ai_chat_tables"
down_revision = "023_create_user_consents"
branch_labels = None
depends_on = None


def _metadata_column_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _metadata_server_default():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade() -> None:
    op.create_table(
        "ai_chat_threads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_chat_threads_user_id", "ai_chat_threads", ["user_id"])
    op.create_index("ix_ai_chat_threads_status", "ai_chat_threads", ["status"])

    op.create_table(
        "ai_chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("ai_chat_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("metadata", _metadata_column_type(), nullable=False, server_default=_metadata_server_default()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_chat_messages_thread_id", "ai_chat_messages", ["thread_id"])
    op.create_index("ix_ai_chat_messages_user_id", "ai_chat_messages", ["user_id"])
    op.create_index("ix_ai_chat_messages_created_at", "ai_chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_chat_messages_created_at", table_name="ai_chat_messages")
    op.drop_index("ix_ai_chat_messages_user_id", table_name="ai_chat_messages")
    op.drop_index("ix_ai_chat_messages_thread_id", table_name="ai_chat_messages")
    op.drop_table("ai_chat_messages")
    op.drop_index("ix_ai_chat_threads_status", table_name="ai_chat_threads")
    op.drop_index("ix_ai_chat_threads_user_id", table_name="ai_chat_threads")
    op.drop_table("ai_chat_threads")
