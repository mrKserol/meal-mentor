"""Ensure users columns for profile and Telegram auth compatibility.

Revision ID: 004_users_profile_telegram
Revises: 003_auth_web
"""

from alembic import op
import sqlalchemy as sa

revision = "004_users_profile_telegram"
down_revision = "003_auth_web"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def _has_column(bind, table: str, column: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "users"):
        return

    if not _has_column(bind, "users", "target_weight_kg"):
        op.add_column("users", sa.Column("target_weight_kg", sa.Float(), nullable=True))
    if not _has_column(bind, "users", "updated_at"):
        op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=True))
    if not _has_column(bind, "users", "subscription_status"):
        op.add_column(
            "users",
            sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="free"),
        )

    # Telegram users may have no email/password at initial web login.
    if _has_column(bind, "users", "email"):
        op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    if _has_column(bind, "users", "hashed_password"):
        op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=True)
    if _has_column(bind, "users", "telegram_id"):
        op.alter_column("users", "telegram_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # No destructive rollback for nullable/compatibility changes.
    pass
