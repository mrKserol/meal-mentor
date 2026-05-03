"""Add prediction, user_text, meal photo paths to meals.

Revision ID: 009_meal_extra
Revises: 008_create_allergens
"""

from alembic import op
import sqlalchemy as sa

revision = "009_meal_extra"
down_revision = "008_create_allergens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meals", sa.Column("prediction", sa.Text(), nullable=True))
    op.add_column("meals", sa.Column("user_text", sa.Text(), nullable=True))
    op.add_column("meals", sa.Column("meal_photo_large", sa.String(length=512), nullable=True))
    op.add_column("meals", sa.Column("meal_photo_thumb", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("meals", "meal_photo_thumb")
    op.drop_column("meals", "meal_photo_large")
    op.drop_column("meals", "user_text")
    op.drop_column("meals", "prediction")
