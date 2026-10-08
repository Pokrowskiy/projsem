from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.review import Review
from app.schemas.review import ReviewCreate
from app.utils.exceptions import ConflictError, NotFoundError


def create_review(db: Session, author_id: int, data: ReviewCreate) -> Review:
    product = db.get(Product, data.product_id)
    if product is None:
        raise NotFoundError("Product not found")
    purchased = db.scalar(
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.buyer_id == author_id, Order.status == OrderStatus.delivered, OrderItem.product_id == data.product_id)
        .limit(1)
    )
    if purchased is None:
        raise ConflictError("A review can be submitted only after a delivered purchase")
    if db.scalar(select(Review.id).where(Review.author_id == author_id, Review.product_id == data.product_id)):
        raise ConflictError("You have already reviewed this product")
    review = Review(author_id=author_id, **data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, product_id: int) -> list[Review]:
    if db.get(Product, product_id) is None:
        raise NotFoundError("Product not found")
    return list(db.scalars(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc(), Review.id.desc())
    ).all())