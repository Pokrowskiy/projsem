from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import logging

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import TAX_RATE
from app.models.cart import CartItem
from app.models.coupon import Coupon
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User, UserRole
from app.utils.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError


logger = logging.getLogger(__name__)


NEXT_STATUS = {
    OrderStatus.new: OrderStatus.confirmed,
    OrderStatus.confirmed: OrderStatus.sent,
    OrderStatus.sent: OrderStatus.delivered,
}


def create_order(
    db: Session,
    buyer_id: int,
    shipping_address: str,
    coupon_code: str | None = None,
    idempotency_key: str | None = None,
) -> Order:
    normalized_coupon = coupon_code.strip().upper() if coupon_code else None
    if idempotency_key:
        existing = db.scalar(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.buyer_id == buyer_id, Order.idempotency_key == idempotency_key)
        )
        if existing is not None:
            if existing.shipping_address != shipping_address or existing.coupon_code != normalized_coupon:
                raise ConflictError("Idempotency key was already used with a different checkout request")
            return existing

    cart_items = db.scalars(
        select(CartItem).where(CartItem.user_id == buyer_id).order_by(CartItem.product_id)
    ).all()
    if not cart_items:
        raise BadRequestError("Cart is empty")
    seller_ids = set(db.scalars(
        select(Product.seller_id).where(Product.id.in_([item.product_id for item in cart_items]))
    ).all())
    if len(seller_ids) > 1:
        raise BadRequestError("Checkout supports products from one seller at a time")

    order_items = []
    subtotal = Decimal("0.00")
    try:
        coupon = None
        if coupon_code:
            coupon = db.scalar(select(Coupon).where(Coupon.code == normalized_coupon))
            if coupon is None or not coupon.is_active:
                raise BadRequestError("Coupon is invalid or inactive")
            if coupon.expires_at is not None:
                expiry = coupon.expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry <= datetime.now(timezone.utc):
                    raise BadRequestError("Coupon has expired")

        for cart_item in cart_items:
            product = db.get(Product, cart_item.product_id)
            if product is None or not product.is_active:
                raise ConflictError("A product in the cart is no longer available")
            result = db.execute(
                update(Product)
                .where(Product.id == product.id, Product.is_active.is_(True), Product.stock >= cart_item.quantity)
                .values(stock=Product.stock - cart_item.quantity)
            )
            if result.rowcount != 1:
                raise ConflictError(f"Insufficient stock for product {product.id}")
            subtotal += product.price * cart_item.quantity
            order_items.append(OrderItem(
                product_id=product.id,
                quantity=cart_item.quantity,
                price_at_purchase=product.price,
            ))

        discount = Decimal("0.00")
        if coupon is not None:
            redemption = db.execute(
                update(Coupon)
                .where(
                    Coupon.id == coupon.id,
                    Coupon.is_active.is_(True),
                    (Coupon.max_redemptions.is_(None) | (Coupon.redemption_count < Coupon.max_redemptions)),
                )
                .values(redemption_count=Coupon.redemption_count + 1)
            )
            if redemption.rowcount != 1:
                raise ConflictError("Coupon redemption limit has been reached")
            discount = (subtotal * coupon.percentage / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        taxable_subtotal = subtotal - discount
        tax = (taxable_subtotal * TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        order = Order(
            buyer_id=buyer_id,
            shipping_address=shipping_address,
            subtotal=subtotal,
            tax=tax,
            discount=discount,
            coupon_code=coupon.code if coupon else None,
            idempotency_key=idempotency_key,
            total=taxable_subtotal + tax,
            items=order_items,
        )
        db.add(order)
        for cart_item in cart_items:
            db.delete(cart_item)
        db.commit()
        db.refresh(order)
        logger.info(
            "Order created",
            extra={"event": "order_created", "user_id": buyer_id, "order_id": order.id, "total": order.total},
        )
        return order
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.buyer_id == buyer_id, Order.idempotency_key == idempotency_key)
            )
            if existing is not None:
                if existing.shipping_address != shipping_address or existing.coupon_code != normalized_coupon:
                    raise ConflictError("Idempotency key was already used with a different checkout request") from None
                return existing
        raise
    except Exception:
        db.rollback()
        raise


def list_orders(db: Session, user: User) -> list[Order]:
    query = select(Order).options(selectinload(Order.items))
    if user.role == UserRole.buyer:
        query = query.where(Order.buyer_id == user.id)
    elif user.role == UserRole.seller:
        query = query.join(Order.items).join(OrderItem.product).where(Product.seller_id == user.id).distinct()
    return list(db.scalars(query.order_by(Order.created_at.desc(), Order.id.desc())).all())


def get_order(db: Session, order_id: int, user: User) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.id == order_id))
    if order is None:
        raise NotFoundError("Order not found")
    if user.role == UserRole.buyer and order.buyer_id != user.id:
        raise ForbiddenError("You cannot access this order")
    if user.role == UserRole.seller and not any(item.product.seller_id == user.id for item in order.items):
        raise ForbiddenError("You cannot access this order")
    return order


def update_status(db: Session, order: Order, user: User, status: OrderStatus) -> Order:
    if status != NEXT_STATUS.get(order.status):
        raise ConflictError(f"Invalid order status transition: {order.status.value} -> {status.value}")
    if user.role == UserRole.seller and any(item.product.seller_id != user.id for item in order.items):
        raise ForbiddenError("Only the seller of every order item can update this order")
    order.status = status
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order: Order, user: User) -> Order:
    if user.role != UserRole.admin and order.buyer_id != user.id:
        raise ForbiddenError("You cannot cancel this order")
    if order.status in (OrderStatus.sent, OrderStatus.delivered, OrderStatus.cancelled):
        raise ConflictError("This order can no longer be cancelled")
    try:
        cancellation = db.execute(
            update(Order)
            .where(Order.id == order.id, Order.status.in_((OrderStatus.new, OrderStatus.confirmed)))
            .values(status=OrderStatus.cancelled)
        )
        if cancellation.rowcount != 1:
            raise ConflictError("This order can no longer be cancelled")
        for item in order.items:
            db.execute(update(Product).where(Product.id == item.product_id).values(stock=Product.stock + item.quantity))
        order.status = OrderStatus.cancelled
        db.commit()
        db.refresh(order)
        logger.info(
            "Order cancelled",
            extra={"event": "order_cancelled", "user_id": user.id, "order_id": order.id},
        )
        return order
    except Exception:
        db.rollback()
        raise