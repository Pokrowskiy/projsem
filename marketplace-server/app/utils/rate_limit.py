from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import RATE_LIMIT, REDIS_URL


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT],
    storage_uri=REDIS_URL or "memory://",
    headers_enabled=True,
)