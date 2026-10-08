from pydantic import BaseModel

from app.schemas.product import ProductRead


class WishlistRead(BaseModel):
    items: list[ProductRead]