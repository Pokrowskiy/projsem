from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemRead, CartRead
from app.utils.exceptions import BadRequestError, NotFoundError


def get_cart(db: Session, user_id: int) -> CartRead:
    items = db.scalars(
        select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.created_at, CartItem.id)
    ).all()
    output = []
    subtotal = Decimal("0.00")
    for item in items:
        product = db.get(Product, item.product_id)
        if product is None or not product.is_active:
            continue
        line_total = product.price * item.quantity
        subtotal += line_total
        output.append(CartItemRead(
            id=item.id,
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            line_total=line_total,
            created_at=item.created_at,
        ))
    return CartRead(items=output, subtotal=subtotal)


def add_item(db: Session, user_id: int, product_id: int, quantity: int) -> CartItem:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError("Product not found")
    item = db.scalar(select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id))
    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > product.stock:
        raise BadRequestError("Requested quantity exceeds available stock")
    if item is None:
        item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(item)
    else:
        item.quantity = new_quantity
    db.commit()
    db.refresh(item)
    return item


def set_quantity(db: Session, user_id: int, product_id: int, quantity: int) -> CartItem:
    item = db.scalar(select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id))
    if item is None:
        raise NotFoundError("Cart item not found")
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError("Product not found")
    if quantity > product.stock:
        raise BadRequestError("Requested quantity exceeds available stock")
    item.quantity = quantity
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, user_id: int, product_id: int) -> None:
    item = db.scalar(select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == product_id))
    if item is None:
        raise NotFoundError("Cart item not found")
    db.delete(item)
    db.commit()