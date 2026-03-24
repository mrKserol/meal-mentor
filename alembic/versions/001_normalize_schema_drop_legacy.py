"""Drop legacy meal_logs/users and create normalized schema.

Revision ID: 001_normalize
Revises:
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

from app.db.models import Base

revision = "001_normalize"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "meal_logs" in tables:
        op.drop_table("meal_logs")

    if "users" in tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "first_name" not in user_cols:
            op.drop_table("users")

    Base.metadata.create_all(bind=conn)


def downgrade() -> None:
    conn = op.get_bind()
    Base.metadata.drop_all(bind=conn)
