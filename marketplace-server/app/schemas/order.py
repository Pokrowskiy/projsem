from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    shipping_address: str = Field(min_length=5, max_length=500)
    coupon_code: str | None = Field(default=None, max_length=40)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    price_at_purchase: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    status: OrderStatus
    shipping_address: str
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    coupon_code: str | None
    total: Decimal
    created_at: datetime
    items: list[OrderItemRead]
