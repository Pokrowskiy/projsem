from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.schemas.cart import CartRead
from app.schemas.product import ProductRead
from app.schemas.wishlist import WishlistRead
from app.services import cart_service
from app.utils.exceptions import ConflictError, NotFoundError


router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=WishlistRead)
def get_wishlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.scalars(
        select(WishlistItem).where(WishlistItem.user_id == user.id).order_by(WishlistItem.created_at.desc())
    ).all()
    products = [db.get(Product, item.product_id) for item in items]
    return WishlistRead(items=[ProductRead.model_validate(product) for product in products if product and product.is_active])


@router.post("/{product_id}", response_model=WishlistRead, status_code=status.HTTP_200_OK)
def add_to_wishlist(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError("Product not found")
    existing = db.scalar(select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id))
    if existing is None:
        db.add(WishlistItem(user_id=user.id, product_id=product_id))
        db.commit()
    return get_wishlist(db, user)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_from_wishlist(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.scalar(select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id))
    if item is None:
        raise NotFoundError("Wishlist item not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{product_id}/cart", response_model=CartRead)
def move_to_cart(product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.scalar(select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id))
    if item is None:
        raise NotFoundError("Wishlist item not found")
    existing_cart_item = db.scalar(select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id))
    if existing_cart_item:
        raise ConflictError("Product is already in the cart")
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError("Product not found")
    if product.stock < 1:
        raise ConflictError("Product is out of stock")
    db.add(CartItem(user_id=user.id, product_id=product_id, quantity=1))
    db.delete(item)
    db.commit()
    return cart_service.get_cart(db, user.id)
