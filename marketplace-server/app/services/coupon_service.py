from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.coupon import Coupon
from app.schemas.coupon import CouponCreate
from app.utils.exceptions import BadRequestError, ConflictError


def create_coupon(db: Session, data: CouponCreate) -> Coupon:
    expires_at = data.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise BadRequestError("Coupon expiry must be in the future")
    coupon = Coupon(
        code=data.code.strip().upper(),
        percentage=data.percentage,
        expires_at=expires_at,
        max_redemptions=data.max_redemptions,
    )
    db.add(coupon)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Coupon.id).where(Coupon.code == coupon.code))
        if existing:
            raise ConflictError("Coupon code already exists") from None
        raise
    db.refresh(coupon)
    return coupon