from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.cart import CartItemWrite, CartRead
from app.services import cart_service
from app.utils.rate_limit import limiter


router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartRead)
def read_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cart_service.get_cart(db, user.id)


@router.post("", response_model=CartRead, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def add_to_cart(
    request: Request,
    response: Response,
    data: CartItemWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cart_service.add_item(db, user.id, data.product_id, data.quantity)
    return cart_service.get_cart(db, user.id)


@router.put("/{product_id}", response_model=CartRead)
def update_cart_item(
    product_id: int,
    data: CartItemWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.product_id != product_id:
        from app.utils.exceptions import BadRequestError

        raise BadRequestError("Product id in path and body must match")
    cart_service.set_quantity(db, user.id, product_id, data.quantity)
    return cart_service.get_cart(db, user.id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_from_cart(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart_service.remove_item(db, user.id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
