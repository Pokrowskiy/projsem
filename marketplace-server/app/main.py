import logging

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routes.auth import router as auth_router
from app.routes.cart import router as cart_router
from app.routes.coupons import router as coupons_router
from app.routes.orders import router as orders_router
from app.routes.products import router as products_router
from app.routes.reviews import router as reviews_router
from app.routes.seller import router as seller_router
from app.routes.users import router as users_router
from app.routes.wishlist import router as wishlist_router
from app.utils.error_handler import register_error_handlers
from app.utils.logger import JsonFormatter
from app.utils.rate_limit import limiter


app = FastAPI(title="Marketplace API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logging.getLogger().handlers[0].setFormatter(JsonFormatter())
register_error_handlers(app)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(cart_router, prefix="/api/v1")
app.include_router(coupons_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(seller_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(wishlist_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
