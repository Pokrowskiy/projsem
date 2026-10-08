from datetime import datetime
from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    image_url: AnyHttpUrl | None = None
    category_id: int = Field(gt=0)
    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    image_url: AnyHttpUrl | None = None
    category_id: int | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Decimal
    image_url: str | None
    category_id: int
    seller_id: int
    stock: int
    is_active: bool
    created_at: datetime
    avg_rating: float = 0


class ProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, gt=0)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
