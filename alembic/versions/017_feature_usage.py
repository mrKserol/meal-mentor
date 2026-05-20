"""Add feature_usage table for AI limit counters."""

from alembic import op
import sqlalchemy as sa

revision = "017_feature_usage"
down_revision = "016_user_auth_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "feature_key",
            "period_type",
            "period_start",
            name="uq_feature_usage_period",
        ),
    )
    op.create_index("ix_feature_usage_user_id", "feature_usage", ["user_id"], unique=False)
    op.create_index("ix_feature_usage_feature_key", "feature_usage", ["feature_key"], unique=False)
    op.create_index("ix_feature_usage_period_start", "feature_usage", ["period_start"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feature_usage_period_start", table_name="feature_usage")
    op.drop_index("ix_feature_usage_feature_key", table_name="feature_usage")
    op.drop_index("ix_feature_usage_user_id", table_name="feature_usage")
    op.drop_table("feature_usage")
