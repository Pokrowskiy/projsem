# Детальное описание архитектуры

## Поток данных

```
HTTP Request
    ↓
Route Handler (routes/*.py)
    ↓
Dependency Injection (dependencies.py)
    ├─ Verify JWT token → Get current user
    └─ Get DB session
    ↓
Validation (Pydantic schemas)
    ↓
Service Layer (services/*.py)
    ├─ Business logic
    ├─ DB queries через ORM
    └─ Exception handling
    ↓
Models (models/*.py)
    ├─ ORM queries к PostgreSQL
    └─ Relationships
    ↓
Response Schema (schemas/*.py)
    ↓
HTTP Response (JSON)
```

## Зависимости между слоями

```
Routes (используют)
  └─ Services
      └─ Models
          └─ Database

Schemas (используются)
  ├─ Routes (input/output)
  └─ Services (внутренние структуры)

Utils (используются везде)
  ├─ Security (auth)
  ├─ Logger (логирование)
  └─ Exceptions (ошибки)
```

## Основные операции

### 1. Регистрация пользователя
```
POST /auth/register
  ├─ Validate schema (UserRegisterSchema)
  ├─ UserService.register(email, password, role)
  │   ├─ Check if email exists (Model.query)
  │   ├─ Hash password (passlib)
  │   └─ Save to DB (SQLAlchemy)
  └─ Return JWT token
```

### 2. Поиск товаров с фильтрацией
```
GET /products?search=phone&min_price=100&max_price=1000&category=electronics
  ├─ Parse filters
  ├─ ProductService.search(filters)
  │   ├─ Build SQLAlchemy query
  │   ├─ LIKE по названию/описанию
  │   ├─ WHERE price BETWEEN
  │   ├─ JOIN с Category
  │   └─ ORDER BY rating DESC
  └─ Return ProductListSchema[]
```

### 3. Создание заказа
```
POST /orders
  ├─ Get current_user from JWT
  ├─ Validate OrderCreateSchema (cart items)
  ├─ OrderService.create_order(user_id, items)
  │   ├─ Check stock для каждого товара
  │   ├─ Lock stock (UPDATE ... FOR UPDATE)
  │   ├─ Calculate total
  │   ├─ Create Order record
  │   ├─ Create OrderItem records
  │   └─ Decrease stock
  ├─ Commit transaction
  └─ Return OrderSchema with order_id
```

### 4. Оставить отзыв
```
POST /reviews
  ├─ Validate ReviewCreateSchema
  ├─ ReviewService.create_review(product_id, user_id, rating, text)
  │   ├─ Check if user bought this product
  │   │   (SELECT COUNT(*) FROM order_items oi
  │   │    JOIN orders o ON oi.order_id = o.id
  │   │    WHERE o.buyer_id = ? AND oi.product_id = ?)
  │   ├─ Check if already reviewed
  │   └─ Save Review
  └─ Return ReviewSchema
```

## Транзакции и откаты

Критические операции используют `try-except` с откатом:
- Создание заказа (блокировка stock)
- Отмена заказа (восстановление stock)
- Удаление товара (удаление зависимостей)

```python
# Пример в Service
def create_order(self, user_id, items):
    try:
        with self.db.begin():  # Transaction
            # Check & lock stock
            # Create order
            # Create items
            # Update stock
        return order
    except Exception as e:
        # Rollback automatic
        raise OrderCreationError(str(e))
```

## Состояние корзины

**Важно:** Корзина хранится **в памяти** (не в БД) = не персистируется между запросами.

Опции:
1. **Session cookie** — малый объем
2. **Redis** — масштабируемо
3. **Database** — простейшее решение для учебного проекта

Для MVP: просто возвращаем пустую корзину при каждом запросе или используем JSON в request body.

```python
class CartService:
    def add_to_cart(self, user_id, product_id, quantity):
        # В реальности: HSET в Redis
        # Для MVP: просто валидируем и возвращаем
        pass
```

## Роли и права доступа

Проверяются в `dependencies.py`:
```python
async def get_current_user(token: str) -> User:
    # Decode JWT
    return user

async def require_seller(user: User = Depends(get_current_user)):
    if user.role != "seller":
        raise HTTPException(status_code=403)
    return user
```

Использование в routes:
```python
@router.post("/products")
def create_product(
    data: ProductCreateSchema,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    return ProductService(db).create(current_user.id, data)
```

## Логирование

Структурированные логи в JSON:
```json
{
  "timestamp": "2026-10-05T10:30:45Z",
  "level": "INFO",
  "event": "order_created",
  "user_id": 123,
  "order_id": 456,
  "total": 99.99,
  "duration_ms": 234
}
```

Все операции логируются в services/utils.

## Обработка ошибок

Кастомные исключения в `utils/exceptions.py`:
```python
class OrderCreationError(Exception): pass
class ProductNotFoundError(Exception): pass
class InsufficientStockError(Exception): pass
class UnauthorizedError(Exception): pass
```

Middleware преобразует их в HTTP ответы (400, 404, 403, etc).