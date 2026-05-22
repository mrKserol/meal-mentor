"""Add user.language and meal/meal_item display name columns."""

from alembic import op
import sqlalchemy as sa

revision = "019_add_user_language_and_food_display_names"
down_revision = "018_seed_plan_features_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("language", sa.String(length=16), nullable=False, server_default="ru"),
    )
    op.add_column("meals", sa.Column("prediction_translated", sa.Text(), nullable=True))
    op.add_column("meals", sa.Column("prediction_language", sa.String(length=16), nullable=True))
    op.add_column("meal_items", sa.Column("name_translated", sa.String(length=255), nullable=True))
    op.add_column("meal_items", sa.Column("name_language", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_items", "name_language")
    op.drop_column("meal_items", "name_translated")
    op.drop_column("meals", "prediction_language")
    op.drop_column("meals", "prediction_translated")
    op.drop_column("users", "language")
