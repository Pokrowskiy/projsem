from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import require_roles
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User, UserRole


router = APIRouter(prefix="/seller", tags=["seller"])


class SellerAnalytics(BaseModel):
    active_products: int
    units_sold: int
    revenue: Decimal


@router.get("/analytics", response_model=SellerAnalytics)
def get_analytics(
    db: Session = Depends(get_db),
    seller: User = Depends(require_roles(UserRole.seller, UserRole.admin)),
):
    products = select(func.count(Product.id)).where(Product.is_active.is_(True))
    sales = (
        select(
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.coalesce(func.sum(OrderItem.price_at_purchase * OrderItem.quantity), 0),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(Product.seller_id == seller.id, Order.status != OrderStatus.cancelled)
    )
    if seller.role != UserRole.admin:
        products = products.where(Product.seller_id == seller.id)
    active_products = db.scalar(products) or 0
    units_sold, revenue = db.execute(sales).one()
    return SellerAnalytics(active_products=active_products, units_sold=units_sold, revenue=revenue)
