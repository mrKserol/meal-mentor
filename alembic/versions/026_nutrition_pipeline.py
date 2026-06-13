"""add nutrition pipeline settings"""

from alembic import op
import sqlalchemy as sa

revision = "026_nutrition_pipeline"
down_revision = "025_ai_chat_pg_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "nutrition_pipeline_version",
            sa.String(length=32),
            nullable=False,
            server_default="global",
        ),
    )
    op.create_index(
        "ix_users_nutrition_pipeline_version",
        "users",
        ["nutrition_pipeline_version"],
    )
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        settings,
        [
            {
                "key": "nutrition_pipeline_global_version",
                "value": "v1_csv",
                "updated_at": None,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_users_nutrition_pipeline_version", table_name="users")
    op.drop_column("users", "nutrition_pipeline_version")
