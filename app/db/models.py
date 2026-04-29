from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    subscription_status = Column(String(32), nullable=False, default="Free")
    first_name = Column(String(255), nullable=True)
    sex = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    target_weight_kg = Column(Float, nullable=True)
    goal = Column(String(100), nullable=True)
    activity_level = Column(String(50), nullable=True)
    timezone = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meals = relationship("Meal", back_populates="user")
    measurements = relationship("UserMeasurement", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


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
    estimated_weight_g = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    confidence = Column(Integer, nullable=True)
    raw_recognition_text = Column(Text, nullable=True)
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
    fiber_g = Column(Integer, nullable=True)
    sugar_g = Column(Integer, nullable=True)
    saturated_fat_g = Column(Float, nullable=True)
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
    vitamin_a_mcg = Column(Float, nullable=True)
    vitamin_c_mg = Column(Float, nullable=True)
    vitamin_d_mcg = Column(Float, nullable=True)
    vitamin_e_mg = Column(Float, nullable=True)
    vitamin_k_mcg = Column(Float, nullable=True)
    vitamin_b6_mg = Column(Float, nullable=True)
    vitamin_b12_mcg = Column(Float, nullable=True)
    folate_mcg = Column(Float, nullable=True)
    thiamin_mg = Column(Float, nullable=True)
    riboflavin_mg = Column(Float, nullable=True)
    niacin_mg = Column(Float, nullable=True)
    pantothenic_acid_mg = Column(Float, nullable=True)
    choline_mg = Column(Float, nullable=True)
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


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    plan = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    provider = Column(String(32), nullable=False, default="robokassa")
    payment_status = Column(String(32), nullable=True)
    external_payment_id = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")


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
