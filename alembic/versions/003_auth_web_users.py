"""Add web auth fields and refresh token rotation table.

Revision ID: 003_auth_web
Revises: 002_extended
"""

from alembic import op
import sqlalchemy as sa

revision = "003_auth_web"
down_revision = "002_extended"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_index(bind, table: str, index_name: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(i["name"] == index_name for i in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_column(bind, "users", "telegram_id"):
        op.alter_column("users", "telegram_id", existing_type=sa.Integer(), nullable=True)

    if not _has_column(bind, "users", "email"):
        op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    if not _has_column(bind, "users", "hashed_password"):
        op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=True))
    if not _has_column(bind, "users", "subscription_status"):
        op.add_column(
            "users",
            sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="free"),
        )

    if not _has_index(bind, "users", "ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "refresh_tokens" not in insp.get_table_names():
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("replaced_by_token_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["replaced_by_token_id"], ["refresh_tokens.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
        op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "refresh_tokens" in insp.get_table_names():
        op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
        op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
        op.drop_table("refresh_tokens")

    if _has_index(bind, "users", "ix_users_email"):
        op.drop_index("ix_users_email", table_name="users")
    if _has_column(bind, "users", "subscription_status"):
        op.drop_column("users", "subscription_status")
    if _has_column(bind, "users", "hashed_password"):
        op.drop_column("users", "hashed_password")
    if _has_column(bind, "users", "email"):
        op.drop_column("users", "email")

    if _has_column(bind, "users", "telegram_id"):
        op.alter_column("users", "telegram_id", existing_type=sa.Integer(), nullable=False)
