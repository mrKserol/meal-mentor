from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS, apply_nutrition_columns_to_model

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    subscription_status = Column(String(32), nullable=False, default="Free")
    role = Column(String(32), nullable=False, default="user", index=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    first_name = Column(String(255), nullable=True)
    sex = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    goal = Column(String(100), nullable=True)
    activity_level = Column(String(50), nullable=True)
    timezone = Column(String(64), nullable=True)
    # ISO 639-1 codes: ru, en, es, de, fr
    language = Column(String(16), nullable=False, default="ru")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meals = relationship("Meal", back_populates="user")
    measurements = relationship("UserMeasurement", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user", foreign_keys="Subscription.user_id")
    feature_overrides = relationship(
        "UserFeatureOverride",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    nutrition_targets = relationship(
        "NutritionTarget",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    allergens = relationship(
        "Allergen",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    auth_identities = relationship(
        "UserAuthIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    consents = relationship(
        "UserConsent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    additives = relationship(
        "Additive",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    additive_intakes = relationship(
        "AdditiveIntake",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    curator_assignments_as_curator = relationship(
        "CuratorUserAssignment",
        foreign_keys="CuratorUserAssignment.curator_id",
        back_populates="curator",
        cascade="all, delete-orphan",
    )
    curator_assignments_as_user = relationship(
        "CuratorUserAssignment",
        foreign_keys="CuratorUserAssignment.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class CuratorUserAssignment(Base):
    """Links a curator (or admin acting as curator) to a supervised user."""

    __tablename__ = "curator_user_assignments"
    __table_args__ = (
        UniqueConstraint("curator_id", "user_id", name="uq_curator_user_assignment"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    curator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    curator = relationship("User", foreign_keys=[curator_id], back_populates="curator_assignments_as_curator")
    user = relationship("User", foreign_keys=[user_id], back_populates="curator_assignments_as_user")
    created_by_admin = relationship("User", foreign_keys=[created_by_admin_id])


class UserAuthIdentity(Base):
    __tablename__ = "user_auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identity_provider_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    provider = Column(String(32), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False)

    email = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="auth_identities")


class UserConsent(Base):
    __tablename__ = "user_consents"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "consent_type",
            "consent_version",
            name="uq_user_consent_type_version",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False)
    consent_version = Column(String(20), nullable=False)
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_metadata = Column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="consents")


class NutritionTarget(Base):
    __tablename__ = "nutrition_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bmr_kcal = Column(Integer, nullable=False)
    tdee_kcal = Column(Integer, nullable=False)
    target_calories = Column(Integer, nullable=False)
    target_fiber_g = Column(Float, nullable=False, default=0.0)
    target_protein_g = Column(Integer, nullable=False)
    target_fat_g = Column(Integer, nullable=False)
    target_carbs_g = Column(Integer, nullable=False)
    formula_name = Column(String(64), nullable=False, default="mifflin_st_jeor")
    goal = Column(String(100), nullable=True)
    activity_level = Column(String(50), nullable=True)
    weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="nutrition_targets")


class Allergen(Base):
    __tablename__ = "allergens"
    __table_args__ = (
        UniqueConstraint("user_id", "allergen_key", name="uq_allergens_user_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen_key = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="allergens")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price_amount = Column(Integer, nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="RUB")
    period_days = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    features = relationship(
        "PlanFeature",
        back_populates="plan",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship("Subscription", back_populates="plan_ref")


class PlanFeature(Base):
    __tablename__ = "plan_features"
    __table_args__ = (
        UniqueConstraint("plan_id", "feature_key", name="uq_plan_features_plan_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key = Column(String(64), nullable=False)
    feature_name = Column(String(255), nullable=False)
    value_type = Column(String(32), nullable=False, default="limit")
    value_bool = Column(Boolean, nullable=True)
    value_int = Column(Integer, nullable=True)
    value_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan = relationship("Plan", back_populates="features")


class UserFeatureOverride(Base):
    __tablename__ = "user_feature_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "feature_key", name="uq_user_feature_overrides_user_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key = Column(String(64), nullable=False)
    value_type = Column(String(32), nullable=False, default="limit")
    value_bool = Column(Boolean, nullable=True)
    value_int = Column(Integer, nullable=True)
    value_text = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="feature_overrides")


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    telegram_file_id = Column(String(255), nullable=True)
    meal_type = Column(String(50), nullable=True)  # breakfast, lunch, dinner, snack
    source_type = Column(String(50), nullable=True)  # photo, text, manual
    meal_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    # item_name / prediction: base/canonical names for nutrition.csv lookup.
    # prediction_translated / MealItem.name_translated: presentation-only; never use for nutrition.
    prediction = Column(Text, nullable=True)
    prediction_translated = Column(Text, nullable=True)
    prediction_language = Column(String(16), nullable=True)
    user_text = Column(Text, nullable=True)
    meal_photo_large = Column(String(512), nullable=True)
    meal_photo_thumb = Column(String(512), nullable=True)

    user = relationship("User", back_populates="meals")
    items = relationship(
        "MealItem",
        back_populates="meal",
        cascade="all, delete-orphan",
    )


class MealItem(Base):
    __tablename__ = "meal_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(ForeignKey("meals.id"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    name_translated = Column(String(255), nullable=True)
    name_language = Column(String(16), nullable=True)
    ingredient_state = Column(String(32), nullable=True)
    estimated_weight_g = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    confidence = Column(Integer, nullable=True)
    raw_recognition_text = Column(Text, nullable=True)
    nutrition_match_name = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meal = relationship("Meal", back_populates="items")
    nutrition = relationship(
        "MealItemNutrition",
        back_populates="item",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MealItemNutrition(Base):
    __tablename__ = "meal_item_nutrition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_item_id = Column(
        ForeignKey("meal_items.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    calories = Column(Integer, nullable=True)
    protein_g = Column(Integer, nullable=True)
    fat_g = Column(Integer, nullable=True)
    carbs_g = Column(Integer, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Integer, nullable=True)
    serving_size_g = Column(Float, nullable=True)
    cholesterol_mg = Column(Float, nullable=True)
    saturated_fat_g = Column(Float, nullable=True)
    folic_acid_mcg = Column(Float, nullable=True)
    sodium_mg = Column(Integer, nullable=True)
    calcium_mg = Column(Float, nullable=True)
    magnesium_mg = Column(Float, nullable=True)
    potassium_mg = Column(Float, nullable=True)
    phosphorus_mg = Column(Float, nullable=True)
    iron_mg = Column(Float, nullable=True)
    zinc_mg = Column(Float, nullable=True)
    selenium_mcg = Column(Float, nullable=True)
    copper_mg = Column(Float, nullable=True)
    manganese_mg = Column(Float, nullable=True)
    vitamin_a_iu = Column(Float, nullable=True)
    vitamin_a_rae_mcg = Column(Float, nullable=True)
    carotene_alpha_mcg = Column(Float, nullable=True)
    carotene_beta_mcg = Column(Float, nullable=True)
    cryptoxanthin_beta_mcg = Column(Float, nullable=True)
    lutein_zeaxanthin_mcg = Column(Float, nullable=True)
    lycopene_mcg = Column(Float, nullable=True)
    vitamin_c_mg = Column(Float, nullable=True)
    vitamin_d_iu = Column(Float, nullable=True)
    vitamin_e_mg = Column(Float, nullable=True)
    tocopherol_alpha_mg = Column(Float, nullable=True)
    vitamin_k_mcg = Column(Float, nullable=True)
    vitamin_b6_mg = Column(Float, nullable=True)
    vitamin_b12_mcg = Column(Float, nullable=True)
    folate_mcg = Column(Float, nullable=True)
    thiamin_mg = Column(Float, nullable=True)
    riboflavin_mg = Column(Float, nullable=True)
    niacin_mg = Column(Float, nullable=True)
    pantothenic_acid_mg = Column(Float, nullable=True)
    choline_mg = Column(Float, nullable=True)
    alanine_g = Column(Float, nullable=True)
    arginine_g = Column(Float, nullable=True)
    aspartic_acid_g = Column(Float, nullable=True)
    cystine_g = Column(Float, nullable=True)
    glutamic_acid_g = Column(Float, nullable=True)
    glycine_g = Column(Float, nullable=True)
    histidine_g = Column(Float, nullable=True)
    hydroxyproline_g = Column(Float, nullable=True)
    isoleucine_g = Column(Float, nullable=True)
    leucine_g = Column(Float, nullable=True)
    lysine_g = Column(Float, nullable=True)
    methionine_g = Column(Float, nullable=True)
    phenylalanine_g = Column(Float, nullable=True)
    proline_g = Column(Float, nullable=True)
    serine_g = Column(Float, nullable=True)
    threonine_g = Column(Float, nullable=True)
    tryptophan_g = Column(Float, nullable=True)
    tyrosine_g = Column(Float, nullable=True)
    valine_g = Column(Float, nullable=True)
    fructose_g = Column(Float, nullable=True)
    galactose_g = Column(Float, nullable=True)
    glucose_g = Column(Float, nullable=True)
    lactose_g = Column(Float, nullable=True)
    maltose_g = Column(Float, nullable=True)
    sucrose_g = Column(Float, nullable=True)
    total_fat_g = Column(Float, nullable=True)
    saturated_fatty_acids_g = Column(Float, nullable=True)
    monounsaturated_fatty_acids_g = Column(Float, nullable=True)
    polyunsaturated_fatty_acids_g = Column(Float, nullable=True)
    fatty_acids_total_trans_mg = Column(Float, nullable=True)
    alcohol_g = Column(Float, nullable=True)
    ash_g = Column(Float, nullable=True)
    caffeine_mg = Column(Float, nullable=True)
    theobromine_mg = Column(Float, nullable=True)
    water_g = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("MealItem", back_populates="nutrition")


class DailySummary(Base):
    __tablename__ = "daily_summary"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_summary_user_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    total_calories = Column(Integer, nullable=True)
    total_protein_g = Column(Integer, nullable=True)
    total_fat_g = Column(Integer, nullable=True)
    total_carbs_g = Column(Integer, nullable=True)
    meal_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class FeatureUsage(Base):
    __tablename__ = "feature_usage"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "feature_key",
            "period_type",
            "period_start",
            name="uq_feature_usage_period",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key = Column(String(64), nullable=False, index=True)
    period_type = Column(String(16), nullable=False)
    period_start = Column(Date, nullable=False, index=True)
    used_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True, index=True)
    activated_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    plan = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    provider = Column(String(32), nullable=False, default="robokassa")
    payment_status = Column(String(32), nullable=True)
    external_payment_id = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions", foreign_keys=[user_id])
    plan_ref = relationship("Plan", back_populates="subscriptions")
    activated_by_admin = relationship("User", foreign_keys=[activated_by_admin_id])


class RecommendationsLog(Base):
    __tablename__ = "recommendations_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    recommendation_text = Column(Text, nullable=False)
    reason_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class UserMeasurement(Base):
    __tablename__ = "user_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    measured_at = Column(DateTime, nullable=False)
    weight_kg = Column(Float, nullable=True)
    waist_cm = Column(Float, nullable=True)
    body_fat_percent = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="measurements")


class AiChatThread(Base):
    __tablename__ = "ai_chat_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    title = Column(String(255), nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    messages = relationship(
        "AiChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class AiChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(Integer, ForeignKey("ai_chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    extra_metadata = Column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    thread = relationship("AiChatThread", back_populates="messages")
    user = relationship("User")


class Additive(Base):
    __tablename__ = "additives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    additive_name = Column(String(255), nullable=False)
    photo_large = Column(String(512), nullable=True)
    photo_thumb = Column(String(512), nullable=True)
    serving_label = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="additives")
    intakes = relationship("AdditiveIntake", back_populates="additive")


apply_nutrition_columns_to_model(Additive)


class AdditiveIntake(Base):
    __tablename__ = "additive_intakes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    additive_id = Column(Integer, ForeignKey("additives.id", ondelete="SET NULL"), nullable=True, index=True)
    additive_name_snapshot = Column(String(255), nullable=False)
    servings_count = Column(Float, nullable=False, default=1.0)
    intake_datetime = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="additive_intakes")
    additive = relationship("Additive", back_populates="intakes")


apply_nutrition_columns_to_model(AdditiveIntake)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_token_id = Column(ForeignKey("refresh_tokens.id"), nullable=True)

    user = relationship("User", back_populates="refresh_tokens", foreign_keys=[user_id])
