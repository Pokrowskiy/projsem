from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.coupon import CouponCreate, CouponRead
from app.services.coupon_service import create_coupon


router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("", response_model=CouponRead, status_code=status.HTTP_201_CREATED)
def add_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    return create_coupon(db, data)