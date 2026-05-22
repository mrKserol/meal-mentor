"""Create curator_user_assignments table."""

from alembic import op
import sqlalchemy as sa

revision = "020_curator_assignments"
down_revision = "019_add_multilang_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curator_user_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("curator_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["curator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("curator_id", "user_id", name="uq_curator_user_assignment"),
        sa.CheckConstraint("curator_id <> user_id", name="ck_curator_user_assignment_distinct"),
    )
    op.create_index("ix_curator_user_assignments_curator_id", "curator_user_assignments", ["curator_id"])
    op.create_index("ix_curator_user_assignments_user_id", "curator_user_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_curator_user_assignments_user_id", table_name="curator_user_assignments")
    op.drop_index("ix_curator_user_assignments_curator_id", table_name="curator_user_assignments")
    op.drop_table("curator_user_assignments")
