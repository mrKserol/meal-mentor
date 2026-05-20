"""Add user_auth_identities for multi-provider OAuth."""

from alembic import op
import sqlalchemy as sa

revision = "016_user_auth_identities"
down_revision = "015_admin_plans_entitlements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_auth_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_auth_identity_provider_user"),
    )
    op.create_index("ix_user_auth_identities_user_id", "user_auth_identities", ["user_id"], unique=False)
    op.create_index("ix_user_auth_identities_provider", "user_auth_identities", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_auth_identities_provider", table_name="user_auth_identities")
    op.drop_index("ix_user_auth_identities_user_id", table_name="user_auth_identities")
    op.drop_table("user_auth_identities")
