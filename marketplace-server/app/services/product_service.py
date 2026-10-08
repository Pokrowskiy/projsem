from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.review import Review
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.exceptions import NotFoundError


def get_product(db: Session, product_id: int, include_inactive: bool = False) -> Product:
    product = db.get(Product, product_id)
    if product is None or (not include_inactive and not product.is_active):
        raise NotFoundError("Product not found")
    return product


def list_products(
    db: Session,
    search: str | None,
    category_id: int | None,
    min_price: float | None,
    max_price: float | None,
    min_rating: float | None,
    in_stock: bool,
    limit: int,
    offset: int,
):
    rating_by_product = (
        select(Review.product_id, func.avg(Review.rating).label("average"))
        .group_by(Review.product_id)
        .subquery()
    )
    conditions = [Product.is_active.is_(True)]
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(Product.name.ilike(pattern) | Product.description.ilike(pattern))
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if min_price is not None:
        conditions.append(Product.price >= min_price)
    if max_price is not None:
        conditions.append(Product.price <= max_price)
    if min_rating is not None:
        conditions.append(rating_by_product.c.average >= min_rating)
    if in_stock:
        conditions.append(Product.stock > 0)

    total = db.scalar(select(func.count()).select_from(Product).outerjoin(
        rating_by_product, rating_by_product.c.product_id == Product.id
    ).where(*conditions)) or 0
    rows = db.execute(
        select(Product, func.coalesce(rating_by_product.c.average, 0.0).label("avg_rating"))
        .outerjoin(rating_by_product, rating_by_product.c.product_id == Product.id)
        .where(*conditions)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [{**{"product": product, "avg_rating": float(rating or 0)}} for product, rating in rows], total


def create_product(db: Session, seller_id: int, data: ProductCreate) -> Product:
    if db.get(Category, data.category_id) is None:
        raise NotFoundError("Category not found")
    product = Product(seller_id=seller_id, **data.model_dump(mode="json"))
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, data: ProductUpdate) -> Product:
    changes = data.model_dump(exclude_unset=True, mode="json")
    category_id = changes.get("category_id")
    if category_id is not None and db.get(Category, category_id) is None:
        raise NotFoundError("Category not found")
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def get_average_rating(db: Session, product_id: int) -> float:
    return float(db.scalar(select(func.avg(Review.rating)).where(Review.product_id == product_id)) or 0)


def create_category(db: Session, name: str, parent_id: int | None) -> Category:
    if parent_id is not None and db.get(Category, parent_id) is None:
        raise NotFoundError("Parent category not found")
    category = Category(name=name.strip(), parent_id=parent_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
