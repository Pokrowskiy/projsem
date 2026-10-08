from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    product_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=5000)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    author_id: int
    rating: int
    text: str
    created_at: datetime
