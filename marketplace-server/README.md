# Marketplace API

Versioned REST API built with FastAPI, SQLAlchemy 2, Pydantic 2, Alembic and PostgreSQL. SQLite is the default for local development and tests.

## Run locally

```powershell
cd marketplace-server
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.cli create-admin admin@example.com
uvicorn app.main:app --reload
```

Set a unique `JWT_SECRET` in `.env` before using the service outside local development. Set `DATABASE_URL` to a PostgreSQL 15+ URL for a shared deployment. `TAX_RATE` is a decimal fraction (`0.20` for 20%); it defaults to zero. All prices and totals use decimal arithmetic. Coupon discounts are applied before tax.

Set `REDIS_URL` in a multi-worker deployment to share rate-limit state across API instances. Without it, rate limiting uses process-local memory and is suitable only for local development or a single worker. `RATE_LIMIT` controls the default limit (default: `60/minute`); authentication endpoints use `10/minute`.

## API

Interactive OpenAPI docs are available at `/docs`; all business endpoints are under `/api/v1`.

| Area | Endpoints |
|---|---|
| Auth/profile | `POST /auth/register`, `POST /auth/login`, `GET /users/me`, `PATCH /users/me` |
| Catalog | `GET /products`, `GET /products/{id}`, seller `POST/PATCH/DELETE /products` |
| Categories | `GET /categories`, admin `POST /categories` |
| Cart | `GET/POST /cart`, `PUT/DELETE /cart/{product_id}` |
| Orders | `POST/GET /orders`, `GET /orders/{id}`, seller/admin status updates, buyer cancellation |
| Reviews | `POST /reviews`, `GET /products/{id}/reviews` |
| Wishlist | `GET/POST /wishlist`, `DELETE /wishlist/{product_id}`, `POST /wishlist/{product_id}/cart` |
| Coupons | Admin `POST /coupons`; checkout accepts an optional `coupon_code` |
| Seller | `GET /seller/analytics` |

Registration permits only `buyer` and `seller`; bootstrap administrators through the CLI. Orders are created from the persisted cart; each checkout currently supports products from one seller so fulfillment status has a single owner. Stock is decremented conditionally inside the checkout transaction and restored on eligible cancellation. Reviews require a delivered order and are unique per buyer/product. Product deletion is a soft delete so order history remains intact.

Checkout accepts the optional `Idempotency-Key` header (up to 128 characters). Repeating the same key and payload for a buyer returns the original order; reusing the key with a different address or coupon returns `409`.

The API does not process payments or calculate shipping fees. Discounts are percentage coupons created by an administrator; coupon redemption limits are checked transactionally. Domain errors use `{ "error": "...", "message": "..." }`. Structured JSON logs include order identifiers and totals.

## Migrations and tests

```powershell
alembic upgrade head
python -m pytest -q
python -m pytest --cov=app --cov-report=term-missing
```

After changing ORM models, create a migration with `alembic revision --autogenerate -m "describe change"`, inspect it, then apply it with `alembic upgrade head`. Tests use an isolated in-memory SQLite database.