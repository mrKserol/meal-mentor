"""add product nutrition cache tables"""

from alembic import op
import sqlalchemy as sa

from app.db.nutrition_columns import INTEGER_NUTRITION_KEYS, MEAL_ITEM_NUTRITION_KEYS

revision = "027_product_nutrition_cache"
down_revision = "026_nutrition_pipeline"
branch_labels = None
depends_on = None


def _nutrient_columns() -> list[sa.Column]:
    cols: list[sa.Column] = []
    for key in MEAL_ITEM_NUTRITION_KEYS:
        col_type = sa.Integer() if key in INTEGER_NUTRITION_KEYS else sa.Float()
        cols.append(sa.Column(key, col_type, nullable=True))
    return cols


def upgrade() -> None:
    op.create_table(
        "product_nutrition",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_food_id", sa.String(length=128), nullable=True),
        sa.Column("normalized_query", sa.String(length=512), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("description", sa.String(length=512), nullable=False),
        sa.Column("data_type", sa.String(length=64), nullable=True),
        sa.Column("food_category", sa.String(length=255), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_status", sa.String(length=32), nullable=False, server_default="matched"),
        *_nutrient_columns(),
        sa.Column("nutrients_per_100g_json", sa.Text(), nullable=True),
        sa.Column("raw_source_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_product_nutrition_source", "product_nutrition", ["source"])
    op.create_index("ix_product_nutrition_source_food_id", "product_nutrition", ["source_food_id"])
    op.create_index("ix_product_nutrition_normalized_query", "product_nutrition", ["normalized_query"])
    op.create_index("ix_product_nutrition_state", "product_nutrition", ["state"])
    op.create_index("ix_product_nutrition_description", "product_nutrition", ["description"])
    op.create_index("ix_product_nutrition_data_type", "product_nutrition", ["data_type"])
    op.create_index("ix_product_nutrition_match_status", "product_nutrition", ["match_status"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_product_nutrition_source_food_id",
            "product_nutrition",
            ["source", "source_food_id"],
            unique=True,
            postgresql_where=sa.text("source_food_id IS NOT NULL"),
        )
    else:
        op.create_index(
            "ix_product_nutrition_source_food_id_pair",
            "product_nutrition",
            ["source", "source_food_id"],
        )

    op.create_table(
        "product_nutrition_matches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("normalized_query", sa.String(length=512), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("product_nutrition_id", sa.Integer(), sa.ForeignKey("product_nutrition.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_status", sa.String(length=32), nullable=False, server_default="matched"),
        sa.Column("selected_description", sa.String(length=512), nullable=True),
        sa.Column("selected_source_food_id", sa.String(length=128), nullable=True),
        sa.Column("selected_data_type", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "normalized_query",
            "state",
            "source",
            name="uq_product_nutrition_match_query_state_source",
        ),
    )
    op.create_index("ix_product_nutrition_matches_normalized_query", "product_nutrition_matches", ["normalized_query"])
    op.create_index("ix_product_nutrition_matches_state", "product_nutrition_matches", ["state"])
    op.create_index("ix_product_nutrition_matches_source", "product_nutrition_matches", ["source"])
    op.create_index("ix_product_nutrition_matches_product_nutrition_id", "product_nutrition_matches", ["product_nutrition_id"])
    op.create_index("ix_product_nutrition_matches_match_status", "product_nutrition_matches", ["match_status"])
    op.create_index(
        "ix_product_nutrition_matches_query_state_source",
        "product_nutrition_matches",
        ["normalized_query", "state", "source"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_product_nutrition_source_food_id", table_name="product_nutrition")
    else:
        op.drop_index("ix_product_nutrition_source_food_id_pair", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_matches_query_state_source", table_name="product_nutrition_matches")
    op.drop_index("ix_product_nutrition_matches_match_status", table_name="product_nutrition_matches")
    op.drop_index("ix_product_nutrition_matches_product_nutrition_id", table_name="product_nutrition_matches")
    op.drop_index("ix_product_nutrition_matches_source", table_name="product_nutrition_matches")
    op.drop_index("ix_product_nutrition_matches_state", table_name="product_nutrition_matches")
    op.drop_index("ix_product_nutrition_matches_normalized_query", table_name="product_nutrition_matches")
    op.drop_table("product_nutrition_matches")
    op.drop_index("ix_product_nutrition_match_status", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_data_type", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_description", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_state", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_normalized_query", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_source_food_id", table_name="product_nutrition")
    op.drop_index("ix_product_nutrition_source", table_name="product_nutrition")
    op.drop_table("product_nutrition")
