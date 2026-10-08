import os
from decimal import Decimal

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./marketplace.db")
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
TAX_RATE = Decimal(os.getenv("TAX_RATE", "0"))
REDIS_URL = os.getenv("REDIS_URL")
RATE_LIMIT = os.getenv("RATE_LIMIT", "60/minute")
APP_ENV = os.getenv("APP_ENV", "development").lower()

if APP_ENV == "production" and (
	JWT_SECRET == "local-development-secret-change-me" or len(JWT_SECRET) < 32
):
	raise RuntimeError("Production requires a unique JWT_SECRET with at least 32 characters")
