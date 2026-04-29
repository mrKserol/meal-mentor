"""Change users.telegram_id from Integer to BigInteger.

Revision ID: 006_users_telegram_bigint
Revises: 005_users_nullable_free
"""

from alembic import op
import sqlalchemy as sa

revision = "006_users_telegram_bigint"
down_revision = "005_users_nullable_free"
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
    if not _has_column(bind, "users", "telegram_id"):
        return

    # PostgreSQL-safe cast, preserves all existing values.
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="telegram_id::bigint",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "users", "telegram_id"):
        return

    # Downgrade may fail if values exceed int32 range.
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="telegram_id::integer",
    )

