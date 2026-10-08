from app.models.category import Category
from app.models.product import Product
from datetime import datetime, timedelta, timezone
from app.models.user import User, UserRole
from app.utils.security import create_access_token, hash_password


def register(client, email, role):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "role": role},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_admin_token(database):
    db = database()
    admin = User(email="admin@example.com", password_hash=hash_password("admin-password"), role=UserRole.admin)
    db.add(admin)
    db.commit()
    token = create_access_token(admin.id)
    db.close()
    return token


def test_catalog_checkout_delivery_review_and_analytics(client, database):
    db = database()
    category = Category(name="Phones")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    seller_token = register(client, "seller@example.com", "seller")
    buyer_token = register(client, "buyer@example.com", "buyer")
    seller_headers = auth(seller_token)
    buyer_headers = auth(buyer_token)

    created = client.post(
        "/api/v1/products",
        headers=seller_headers,
        json={"name": "Phone One", "description": "A test phone", "price": "20.00", "category_id": category_id, "stock": 5},
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    assert client.get("/api/v1/products?search=phone&in_stock=true").json()["total"] == 1
    assert client.post(
        "/api/v1/cart",
        headers=buyer_headers,
        json={"product_id": product_id, "quantity": 2},
    ).json()["subtotal"] == "40.00"

    order_response = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={"shipping_address": "10 Market Street, London"},
    )
    assert order_response.status_code == 201, order_response.text
    order = order_response.json()
    assert order["total"] == "40.00"
    assert order["items"][0]["quantity"] == 2
    assert client.get("/api/v1/cart", headers=buyer_headers).json()["items"] == []

    other_buyer = auth(register(client, "other-buyer@example.com", "buyer"))
    assert client.get(f"/api/v1/orders/{order['id']}", headers=other_buyer).status_code == 403

    for next_status in ("confirmed", "sent", "delivered"):
        changed = client.patch(
            f"/api/v1/orders/{order['id']}/status",
            headers=seller_headers,
            json={"status": next_status},
        )
        assert changed.status_code == 200, changed.text

    review = client.post(
        "/api/v1/reviews",
        headers=buyer_headers,
        json={"product_id": product_id, "rating": 5, "text": "Excellent"},
    )
    assert review.status_code == 201, review.text
    assert client.get(f"/api/v1/products/{product_id}").json()["avg_rating"] == 5.0
    assert client.post(
        "/api/v1/reviews",
        headers=buyer_headers,
        json={"product_id": product_id, "rating": 5},
    ).status_code == 409

    analytics = client.get("/api/v1/seller/analytics", headers=seller_headers)
    assert analytics.status_code == 200
    assert analytics.json() == {"active_products": 1, "units_sold": 2, "revenue": "40.00"}


def test_cancel_order_restores_stock(client, database):
    db = database()
    category = Category(name="Books")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    seller = auth(register(client, "seller2@example.com", "seller"))
    buyer = auth(register(client, "buyer2@example.com", "buyer"))
    product = client.post(
        "/api/v1/products",
        headers=seller,
        json={"name": "Book", "price": "12.50", "category_id": category_id, "stock": 3},
    ).json()
    client.post("/api/v1/cart", headers=buyer, json={"product_id": product["id"], "quantity": 2})
    order = client.post("/api/v1/orders", headers=buyer, json={"shipping_address": "1 Main Road"}).json()

    cancelled = client.patch(f"/api/v1/orders/{order['id']}/cancel", headers=buyer)
    assert cancelled.status_code == 200
    assert client.get(f"/api/v1/products/{product['id']}").json()["stock"] == 3
    assert client.patch(f"/api/v1/orders/{order['id']}/cancel", headers=buyer).status_code == 409
    assert client.get(f"/api/v1/products/{product['id']}").json()["stock"] == 3


def test_wishlist_item_can_move_to_cart(client, database):
    db = database()
    category = Category(name="Games")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    seller = auth(register(client, "seller3@example.com", "seller"))
    buyer = auth(register(client, "buyer3@example.com", "buyer"))
    product = client.post(
        "/api/v1/products",
        headers=seller,
        json={"name": "Game", "price": "9.99", "category_id": category_id, "stock": 4},
    ).json()

    assert client.post(f"/api/v1/wishlist/{product['id']}", headers=buyer).status_code == 200
    moved = client.post(f"/api/v1/wishlist/{product['id']}/cart", headers=buyer)
    assert moved.status_code == 200
    assert moved.json()["items"][0]["product_id"] == product["id"]
    assert client.get("/api/v1/wishlist", headers=buyer).json()["items"] == []


def test_product_update_delete_and_cart_quantity_permissions(client, database):
    db = database()
    category = Category(name="Wearables")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    seller = auth(register(client, "seller-edit@example.com", "seller"))
    other_seller = auth(register(client, "seller-other@example.com", "seller"))
    buyer = auth(register(client, "buyer-edit@example.com", "buyer"))
    product = client.post(
        "/api/v1/products",
        headers=seller,
        json={"name": "Watch", "price": "75.00", "category_id": category_id, "stock": 5},
    ).json()

    updated = client.patch(
        f"/api/v1/products/{product['id']}",
        headers=seller,
        json={"price": "70.00", "stock": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "70.00"
    assert client.patch(
        f"/api/v1/products/{product['id']}",
        headers=other_seller,
        json={"price": "1.00"},
    ).status_code == 403

    assert client.post(
        "/api/v1/cart",
        headers=buyer,
        json={"product_id": product["id"], "quantity": 1},
    ).status_code == 200
    changed_cart = client.put(
        f"/api/v1/cart/{product['id']}",
        headers=buyer,
        json={"product_id": product["id"], "quantity": 2},
    )
    assert changed_cart.status_code == 200
    assert changed_cart.json()["items"][0]["quantity"] == 2
    assert client.delete(f"/api/v1/cart/{product['id']}", headers=buyer).status_code == 204
    assert client.delete(f"/api/v1/products/{product['id']}", headers=seller).status_code == 204
    assert client.get(f"/api/v1/products/{product['id']}").status_code == 404


def test_checkout_idempotency_key_returns_original_order(client, database):
    db = database()
    category = Category(name="Audio")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    seller = auth(register(client, "seller-idempotent@example.com", "seller"))
    buyer = auth(register(client, "buyer-idempotent@example.com", "buyer"))
    product = client.post(
        "/api/v1/products",
        headers=seller,
        json={"name": "Headphones", "price": "50.00", "category_id": category_id, "stock": 2},
    ).json()
    client.post("/api/v1/cart", headers=buyer, json={"product_id": product["id"], "quantity": 1})

    headers = {**buyer, "Idempotency-Key": "checkout-request-1"}
    payload = {"shipping_address": "5 Market Road"}
    first = client.post("/api/v1/orders", headers=headers, json=payload)
    repeated = client.post("/api/v1/orders", headers=headers, json=payload)
    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    changed_request = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"shipping_address": "6 Different Street"},
    )
    assert changed_request.status_code == 409
    assert client.get(f"/api/v1/products/{product['id']}").json()["stock"] == 1


def test_coupon_discount_and_redemption_limit_are_transactional(client, database):
    db = database()
    category = Category(name="Accessories")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    admin = auth(create_admin_token(database))
    seller = auth(register(client, "seller-coupon@example.com", "seller"))
    first_buyer = auth(register(client, "buyer-coupon-1@example.com", "buyer"))
    second_buyer = auth(register(client, "buyer-coupon-2@example.com", "buyer"))
    product = client.post(
        "/api/v1/products",
        headers=seller,
        json={"name": "Cable", "price": "100.00", "category_id": category_id, "stock": 3},
    ).json()

    coupon = client.post(
        "/api/v1/coupons",
        headers=admin,
        json={"code": "save10", "percentage": "10", "max_redemptions": 1},
    )
    assert coupon.status_code == 201, coupon.text
    duplicate_coupon = client.post(
        "/api/v1/coupons",
        headers=admin,
        json={"code": "SAVE10", "percentage": "5"},
    )
    assert duplicate_coupon.status_code == 409
    assert client.post(
        "/api/v1/coupons",
        headers=first_buyer,
        json={"code": "buyer-coupon", "percentage": "5"},
    ).status_code == 403
    client.post("/api/v1/cart", headers=first_buyer, json={"product_id": product["id"], "quantity": 1})
    first_order = client.post(
        "/api/v1/orders",
        headers=first_buyer,
        json={"shipping_address": "7 Market Road", "coupon_code": "save10"},
    )
    assert first_order.status_code == 201, first_order.text
    assert first_order.json()["subtotal"] == "100.00"
    assert first_order.json()["discount"] == "10.00"
    assert first_order.json()["total"] == "90.00"

    client.post("/api/v1/cart", headers=second_buyer, json={"product_id": product["id"], "quantity": 1})
    second_order = client.post(
        "/api/v1/orders",
        headers=second_buyer,
        json={"shipping_address": "8 Market Road", "coupon_code": "SAVE10"},
    )
    assert second_order.status_code == 409
    assert client.get("/api/v1/products/" + str(product["id"])).json()["stock"] == 2
    assert len(client.get("/api/v1/cart", headers=second_buyer).json()["items"]) == 1

    expired = client.post(
        "/api/v1/coupons",
        headers=admin,
        json={
            "code": "expired",
            "percentage": "5",
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
    )
    assert expired.status_code == 400


def test_checkout_with_stale_cart_stock_rolls_back(client, database):
    db = database()
    category = Category(name="Storage")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    seller = auth(register(client, "seller-stock@example.com", "seller"))
    first_buyer = auth(register(client, "buyer-stock-1@example.com", "buyer"))
    second_buyer = auth(register(client, "buyer-stock-2@example.com", "buyer"))
    product = client.post(
        "/api/v1/products",
        headers=seller,
        json={"name": "Drive", "price": "30.00", "category_id": category_id, "stock": 2},
    ).json()
    client.post("/api/v1/cart", headers=first_buyer, json={"product_id": product["id"], "quantity": 1})
    client.post("/api/v1/cart", headers=second_buyer, json={"product_id": product["id"], "quantity": 1})
    db = database()
    db.get(Product, product["id"]).stock = 1
    db.commit()
    db.close()

    first_order = client.post("/api/v1/orders", headers=first_buyer, json={"shipping_address": "9 Market Road"})
    assert first_order.status_code == 201
    failed_checkout = client.post(
        "/api/v1/orders",
        headers=second_buyer,
        json={"shipping_address": "10 Market Road"},
    )
    assert failed_checkout.status_code == 409
    assert client.get(f"/api/v1/products/{product['id']}").json()["stock"] == 0
    assert len(client.get("/api/v1/cart", headers=second_buyer).json()["items"]) == 1


def test_checkout_rejects_products_from_multiple_sellers(client, database):
    db = database()
    category = Category(name="Multi seller")
    db.add(category)
    db.commit()
    category_id = category.id
    db.close()

    first_seller = auth(register(client, "seller-multi-1@example.com", "seller"))
    second_seller = auth(register(client, "seller-multi-2@example.com", "seller"))
    buyer = auth(register(client, "buyer-multi@example.com", "buyer"))
    first_product = client.post(
        "/api/v1/products",
        headers=first_seller,
        json={"name": "First item", "price": "10.00", "category_id": category_id, "stock": 2},
    ).json()
    second_product = client.post(
        "/api/v1/products",
        headers=second_seller,
        json={"name": "Second item", "price": "12.00", "category_id": category_id, "stock": 2},
    ).json()
    client.post("/api/v1/cart", headers=buyer, json={"product_id": first_product["id"], "quantity": 1})
    client.post("/api/v1/cart", headers=buyer, json={"product_id": second_product["id"], "quantity": 1})

    checkout = client.post("/api/v1/orders", headers=buyer, json={"shipping_address": "11 Market Road"})
    assert checkout.status_code == 400
    assert checkout.json()["message"] == "Checkout supports products from one seller at a time"
    assert len(client.get("/api/v1/cart", headers=buyer).json()["items"]) == 2


def test_health_and_openapi_are_available(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/openapi.json").status_code == 200