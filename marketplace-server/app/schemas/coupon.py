from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    percentage: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)
    expires_at: datetime | None = None
    max_redemptions: int | None = Field(default=None, gt=0)


class CouponRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    percentage: Decimal
    is_active: bool
    expires_at: datetime | None
    max_redemptions: int | None
    redemption_count: int