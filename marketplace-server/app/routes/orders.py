from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services import order_service
from app.utils.exceptions import ForbiddenError
from app.utils.rate_limit import limiter


router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_order(
    request: Request,
    response: Response,
    data: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return order_service.create_order(db, user.id, data.shipping_address, data.coupon_code, idempotency_key)


@router.get("", response_model=list[OrderRead])
def list_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return order_service.list_orders(db, user)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return order_service.get_order(db, order_id, user)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in (UserRole.seller, UserRole.admin):
        raise ForbiddenError("Only sellers and admins can update order status")
    order = order_service.get_order(db, order_id, user)
    return order_service.update_status(db, order, user, data.status)


@router.patch("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_service.get_order(db, order_id, user)
    return order_service.cancel_order(db, order, user)
