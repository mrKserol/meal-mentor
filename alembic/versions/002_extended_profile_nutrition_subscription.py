"""Extended user profile, meal micronutrients, subscriptions.

Revision ID: 002_extended
Revises: 001_normalize
"""
from alembic import op
import sqlalchemy as sa

revision = "002_extended"
down_revision = "001_normalize"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "users", "target_weight_kg"):
        op.add_column("users", sa.Column("target_weight_kg", sa.Float(), nullable=True))

    insp = sa.inspect(bind)
    if "subscriptions" not in insp.get_table_names():
        op.create_table(
            "subscriptions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("plan", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("payment_status", sa.String(length=32), nullable=True),
            sa.Column("external_payment_id", sa.String(length=255), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("ends_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    micron_cols = [
        ("saturated_fat_g", sa.Float()),
        ("calcium_mg", sa.Float()),
        ("magnesium_mg", sa.Float()),
        ("potassium_mg", sa.Float()),
        ("phosphorus_mg", sa.Float()),
        ("iron_mg", sa.Float()),
        ("zinc_mg", sa.Float()),
        ("selenium_mcg", sa.Float()),
        ("copper_mg", sa.Float()),
        ("manganese_mg", sa.Float()),
        ("vitamin_a_mcg", sa.Float()),
        ("vitamin_c_mg", sa.Float()),
        ("vitamin_d_mcg", sa.Float()),
        ("vitamin_e_mg", sa.Float()),
        ("vitamin_k_mcg", sa.Float()),
        ("vitamin_b6_mg", sa.Float()),
        ("vitamin_b12_mcg", sa.Float()),
        ("folate_mcg", sa.Float()),
        ("thiamin_mg", sa.Float()),
        ("riboflavin_mg", sa.Float()),
        ("niacin_mg", sa.Float()),
        ("pantothenic_acid_mg", sa.Float()),
        ("choline_mg", sa.Float()),
    ]
    for name, typ in micron_cols:
        if not _has_column(bind, "meal_item_nutrition", name):
            op.add_column("meal_item_nutrition", sa.Column(name, typ, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    for name, _ in reversed(
        [
            ("choline_mg", None),
            ("pantothenic_acid_mg", None),
            ("niacin_mg", None),
            ("riboflavin_mg", None),
            ("thiamin_mg", None),
            ("folate_mcg", None),
            ("vitamin_b12_mcg", None),
            ("vitamin_b6_mg", None),
            ("vitamin_k_mcg", None),
            ("vitamin_e_mg", None),
            ("vitamin_d_mcg", None),
            ("vitamin_c_mg", None),
            ("vitamin_a_mcg", None),
            ("manganese_mg", None),
            ("copper_mg", None),
            ("selenium_mcg", None),
            ("zinc_mg", None),
            ("iron_mg", None),
            ("phosphorus_mg", None),
            ("potassium_mg", None),
            ("magnesium_mg", None),
            ("calcium_mg", None),
            ("saturated_fat_g", None),
        ]
    ):
        if _has_column(bind, "meal_item_nutrition", name):
            op.drop_column("meal_item_nutrition", name)
    insp = sa.inspect(bind)
    if "subscriptions" in insp.get_table_names():
        op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
        op.drop_table("subscriptions")
    if _has_column(bind, "users", "target_weight_kg"):
        op.drop_column("users", "target_weight_kg")
