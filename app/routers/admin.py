from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_admin
from app.db.models import Plan, PlanFeature, Subscription, User, UserFeatureOverride
from app.db.repository import get_active_subscription
from app.db.session import get_db
from app.schemas.admin import (
    AdminGrantSubscriptionRequest,
    AdminPlanCreateRequest,
    AdminPlanFeatureResponse,
    AdminPlanFeatureUpsertRequest,
    AdminPlanResponse,
    AdminPlanUpdateRequest,
    AdminSubscriptionResponse,
    AdminUserDetail,
    AdminUserFeatureOverrideResponse,
    AdminUserFeatureOverrideUpsertRequest,
    AdminUserListItem,
    AdminUserUpdateRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _get_plan_or_404(db: Session, plan_id: int) -> Plan:
    plan = db.query(Plan).options(joinedload(Plan.features)).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


def _serialize_subscription(sub: Subscription) -> AdminSubscriptionResponse:
    user = sub.user
    plan_ref = sub.plan_ref
    return AdminSubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        user_email=user.email if user else None,
        user_name=(user.first_name or user.username) if user else None,
        plan=sub.plan,
        plan_id=sub.plan_id,
        plan_name=plan_ref.name if plan_ref else None,
        status=sub.status,
        provider=sub.provider,
        payment_status=sub.payment_status,
        started_at=sub.started_at,
        ends_at=sub.ends_at,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        activated_by_admin_id=sub.activated_by_admin_id,
    )


def _serialize_user_list_item(db: Session, user: User) -> AdminUserListItem:
    active_sub = get_active_subscription(db, user.id)
    return AdminUserListItem(
        id=user.id,
        email=user.email,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        role=user.role,
        status=user.status,
        subscription_status=user.subscription_status,
        created_at=user.created_at,
        updated_at=user.updated_at,
        active_subscription_ends_at=active_sub.ends_at if active_sub else None,
    )


def _apply_feature_payload(row: PlanFeature | UserFeatureOverride, payload: AdminPlanFeatureUpsertRequest | AdminUserFeatureOverrideUpsertRequest) -> None:
    row.feature_key = payload.feature_key
    row.value_type = payload.value_type
    row.value_bool = payload.value_bool if payload.value_type == "boolean" else None
    row.value_int = payload.value_int if payload.value_type == "limit" else None
    row.value_text = payload.value_text if payload.value_type == "text" else None
    row.updated_at = datetime.utcnow()


@router.get("/users", response_model=list[AdminUserListItem])
def list_users(
    q: str | None = None,
    role: str | None = None,
    status_q: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = admin
    query = db.query(User).order_by(User.created_at.desc())
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.email.ilike(like),
                User.username.ilike(like),
                User.first_name.ilike(like),
                cast(User.telegram_id, String).ilike(like),
            )
        )
    if role:
        query = query.filter(User.role == role)
    if status_q:
        query = query.filter(User.status == status_q)
    users = query.offset(offset).limit(limit).all()
    return [_serialize_user_list_item(db, user) for user in users]


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = admin
    user = _get_user_or_404(db, user_id)
    active_sub = get_active_subscription(db, user.id)
    subscriptions = (
        db.query(Subscription)
        .options(joinedload(Subscription.user), joinedload(Subscription.plan_ref))
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .limit(20)
        .all()
    )
    overrides = db.query(UserFeatureOverride).filter(UserFeatureOverride.user_id == user.id).order_by(UserFeatureOverride.feature_key).all()
    base = _serialize_user_list_item(db, user).model_dump()
    return AdminUserDetail(
        **base,
        active_subscription=_serialize_subscription(active_sub) if active_sub else None,
        subscriptions=[_serialize_subscription(sub) for sub in subscriptions],
        feature_overrides=[
            AdminUserFeatureOverrideResponse.model_validate(override, from_attributes=True) for override in overrides
        ],
    )


@router.patch("/users/{user_id}", response_model=AdminUserListItem)
def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = admin
    user = _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return _serialize_user_list_item(db, user)


@router.post("/users/{user_id}/block", response_model=AdminUserListItem)
def block_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    user = _get_user_or_404(db, user_id)
    user.status = "blocked"
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return _serialize_user_list_item(db, user)


@router.post("/users/{user_id}/unblock", response_model=AdminUserListItem)
def unblock_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    user = _get_user_or_404(db, user_id)
    user.status = "active"
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return _serialize_user_list_item(db, user)


@router.get("/plans", response_model=list[AdminPlanResponse])
def list_plans(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    return db.query(Plan).options(joinedload(Plan.features)).order_by(Plan.sort_order, Plan.id).all()


@router.post("/plans", response_model=AdminPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(payload: AdminPlanCreateRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    if db.query(Plan).filter(Plan.code == payload.code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan code already exists")
    plan = Plan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _get_plan_or_404(db, plan.id)


@router.get("/plans/{plan_id}", response_model=AdminPlanResponse)
def get_plan(plan_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    return _get_plan_or_404(db, plan_id)


@router.patch("/plans/{plan_id}", response_model=AdminPlanResponse)
def update_plan(plan_id: int, payload: AdminPlanUpdateRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    plan = _get_plan_or_404(db, plan_id)
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != plan.code and db.query(Plan).filter(Plan.code == data["code"]).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan code already exists")
    for field, value in data.items():
        setattr(plan, field, value)
    plan.updated_at = datetime.utcnow()
    db.commit()
    return _get_plan_or_404(db, plan.id)


@router.delete("/plans/{plan_id}", response_model=AdminPlanResponse | dict)
def delete_plan(plan_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    plan = _get_plan_or_404(db, plan_id)
    has_subscriptions = db.query(Subscription.id).filter(Subscription.plan_id == plan.id).first() is not None
    if has_subscriptions:
        plan.is_active = False
        plan.updated_at = datetime.utcnow()
        db.commit()
        return _get_plan_or_404(db, plan.id)
    db.delete(plan)
    db.commit()
    return {"deleted": True}


@router.post("/plans/{plan_id}/features", response_model=AdminPlanFeatureResponse, status_code=status.HTTP_201_CREATED)
def create_plan_feature(plan_id: int, payload: AdminPlanFeatureUpsertRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    _get_plan_or_404(db, plan_id)
    if db.query(PlanFeature).filter(PlanFeature.plan_id == plan_id, PlanFeature.feature_key == payload.feature_key).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Feature already exists for plan")
    feature = PlanFeature(plan_id=plan_id, feature_name=payload.feature_name)
    _apply_feature_payload(feature, payload)
    db.add(feature)
    db.commit()
    db.refresh(feature)
    return feature


@router.patch("/plans/{plan_id}/features/{feature_id}", response_model=AdminPlanFeatureResponse)
def update_plan_feature(plan_id: int, feature_id: int, payload: AdminPlanFeatureUpsertRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    feature = db.query(PlanFeature).filter(PlanFeature.id == feature_id, PlanFeature.plan_id == plan_id).first()
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")
    feature.feature_name = payload.feature_name
    _apply_feature_payload(feature, payload)
    db.commit()
    db.refresh(feature)
    return feature


@router.put("/plans/{plan_id}/features/{feature_key}", response_model=AdminPlanFeatureResponse)
def upsert_plan_feature(plan_id: int, feature_key: str, payload: AdminPlanFeatureUpsertRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    _get_plan_or_404(db, plan_id)
    feature = db.query(PlanFeature).filter(PlanFeature.plan_id == plan_id, PlanFeature.feature_key == feature_key).first()
    if feature is None:
        feature = PlanFeature(plan_id=plan_id)
        db.add(feature)
    feature.feature_key = feature_key
    feature.feature_name = payload.feature_name
    payload.feature_key = feature_key
    _apply_feature_payload(feature, payload)
    db.commit()
    db.refresh(feature)
    return feature


@router.delete("/plans/{plan_id}/features/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_feature(plan_id: int, feature_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    feature = db.query(PlanFeature).filter(PlanFeature.id == feature_id, PlanFeature.plan_id == plan_id).first()
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")
    db.delete(feature)
    db.commit()


@router.get("/subscriptions", response_model=list[AdminSubscriptionResponse])
def list_subscriptions(
    user_id: int | None = None,
    status_q: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = admin
    query = db.query(Subscription).options(joinedload(Subscription.user), joinedload(Subscription.plan_ref)).order_by(Subscription.created_at.desc())
    if user_id is not None:
        query = query.filter(Subscription.user_id == user_id)
    if status_q:
        query = query.filter(Subscription.status == status_q)
    return [_serialize_subscription(sub) for sub in query.offset(offset).limit(limit).all()]


@router.post("/users/{user_id}/grant-subscription", response_model=AdminSubscriptionResponse)
def grant_subscription(user_id: int, payload: AdminGrantSubscriptionRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    plan = _get_plan_or_404(db, payload.plan_id)
    days = payload.days or plan.period_days
    now = datetime.utcnow()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        plan=plan.code,
        status="active",
        provider="admin",
        payment_status="manual",
        started_at=now,
        ends_at=now + timedelta(days=days),
        activated_by_admin_id=admin.id,
    )
    user.subscription_status = plan.name
    user.updated_at = now
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _serialize_subscription(sub)


@router.post("/subscriptions/{subscription_id}/cancel", response_model=AdminSubscriptionResponse)
def cancel_subscription(subscription_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    sub = (
        db.query(Subscription)
        .options(joinedload(Subscription.user), joinedload(Subscription.plan_ref))
        .filter(Subscription.id == subscription_id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    sub.status = "cancelled"
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return _serialize_subscription(sub)


@router.get("/users/{user_id}/feature-overrides", response_model=list[AdminUserFeatureOverrideResponse])
def list_user_feature_overrides(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    _get_user_or_404(db, user_id)
    return db.query(UserFeatureOverride).filter(UserFeatureOverride.user_id == user_id).order_by(UserFeatureOverride.feature_key).all()


@router.put("/users/{user_id}/feature-overrides/{feature_key}", response_model=AdminUserFeatureOverrideResponse)
def upsert_user_feature_override(
    user_id: int,
    feature_key: str,
    payload: AdminUserFeatureOverrideUpsertRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ = admin
    _get_user_or_404(db, user_id)
    override = db.query(UserFeatureOverride).filter(UserFeatureOverride.user_id == user_id, UserFeatureOverride.feature_key == feature_key).first()
    if override is None:
        override = UserFeatureOverride(user_id=user_id)
        db.add(override)
    override.feature_key = feature_key
    payload.feature_key = feature_key
    _apply_feature_payload(override, payload)
    override.reason = payload.reason
    db.commit()
    db.refresh(override)
    return override


@router.delete("/users/{user_id}/feature-overrides/{feature_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_feature_override(user_id: int, feature_key: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    override = db.query(UserFeatureOverride).filter(UserFeatureOverride.user_id == user_id, UserFeatureOverride.feature_key == feature_key).first()
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    db.delete(override)
    db.commit()
