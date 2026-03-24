"""Drop users table.

Revision ID: 002_drop_users
Revises: 001_normalize
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

revision = "002_drop_users"
down_revision = "001_normalize"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("users")


def downgrade() -> None:
    pass
