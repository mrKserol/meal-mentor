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


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    for name, typ in (
        ("prediction", sa.Text()),
        ("user_text", sa.Text()),
        ("meal_photo_large", sa.String(length=512)),
        ("meal_photo_thumb", sa.String(length=512)),
    ):
        if not _has_column(bind, "meals", name):
            op.add_column("meals", sa.Column(name, typ, nullable=True))


def downgrade() -> None:
    op.drop_column("meals", "meal_photo_thumb")
    op.drop_column("meals", "meal_photo_large")
    op.drop_column("meals", "user_text")
    op.drop_column("meals", "prediction")
