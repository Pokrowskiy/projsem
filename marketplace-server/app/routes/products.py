from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.category import Category
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.product import CategoryCreate, CategoryRead, ProductCreate, ProductPage, ProductRead, ProductUpdate
from app.services import product_service
from app.utils.exceptions import ForbiddenError
from app.utils.rate_limit import limiter


router = APIRouter(tags=["products"])


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name, Category.id)).all()


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def add_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    return product_service.create_category(db, data.name, data.parent_id)


@router.get("/products", response_model=ProductPage)
def list_products(
    search: str | None = Query(default=None, max_length=160),
    category_id: int | None = Query(default=None, gt=0),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    in_stock: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price must not exceed max_price")
    rows, total = product_service.list_products(
        db, search, category_id, min_price, max_price, min_rating, in_stock, limit, offset
    )
    items = [ProductRead.model_validate(row["product"]).model_copy(update={"avg_rating": row["avg_rating"]}) for row in rows]
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_product(
    request: Request,
    response: Response,
    data: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.seller, UserRole.admin)),
):
    product = product_service.create_product(db, user.id, data)
    return ProductRead.model_validate(product).model_copy(update={"avg_rating": 0.0})


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = product_service.get_product(db, product_id)
    return ProductRead.model_validate(product).model_copy(update={"avg_rating": product_service.get_average_rating(db, product_id)})


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = product_service.get_product(db, product_id, include_inactive=True)
    if user.role != UserRole.admin and product.seller_id != user.id:
        raise ForbiddenError("Only the product owner can update it")
    product = product_service.update_product(db, product, data)
    return ProductRead.model_validate(product).model_copy(update={"avg_rating": product_service.get_average_rating(db, product_id)})


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = product_service.get_product(db, product_id, include_inactive=True)
    if user.role != UserRole.admin and product.seller_id != user.id:
        raise ForbiddenError("Only the product owner can delete it")
    product.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
