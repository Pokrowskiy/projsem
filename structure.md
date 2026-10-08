# Структура проекта маркетплейса

## Архитектура слоев

```
marketplace-server/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Инициализация FastAPI приложения
│   ├── config.py               # Конфигурация (DB, JWT, etc)
│   ├── dependencies.py         # Dependency Injection (текущий пользователь, DB сессия)
│   │
│   ├── models/                 # SQLAlchemy ORM модели (слой БД)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── order.py
│   │   ├── order_item.py
│   │   ├── review.py
│   │   └── wishlist.py
│   │
│   ├── schemas/                # Pydantic моделипроверки (Request/Response)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── review.py
│   │   └── common.py
│   │
│   ├── services/               # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── user_service.py     # Регистрация, профиль
│   │   ├── product_service.py  # CRUD товаров, поиск
│   │   ├── order_service.py    # Создание, отслеживание заказов
│   │   ├── review_service.py   # Отзывы, рейтинги
│   │   └── cart_service.py     # Корзина (память, не БД)
│   │
│   ├── routes/                 # API эндпоинты
│   │   ├── __init__.py
│   │   ├── auth.py             # POST /auth/register, /auth/login
│   │   ├── users.py            # GET /users/me, PATCH /users/me
│   │   ├── products.py         # GET, POST, PATCH, DELETE /products
│   │   ├── orders.py           # GET, POST /orders
│   │   ├── reviews.py          # GET, POST /reviews
│   │   └── cart.py             # GET, POST, DELETE /cart
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py         # SessionLocal, Base
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, password hashing
│   │   ├── logger.py           # Структурированное логирование
│   │   └── exceptions.py       # Кастомные ошибки
│   │
│   └── middleware/
│       ├── __init__.py
│       └── error_handler.py    # Обработка ошибок
│
├── migrations/                 # Alembic миграции БД
│   └── versions/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Fixtures (test DB, test client)
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
│   └── test_reviews.py
│
├── .env.example                # Пример переменных окружения
├── .gitignore
├── requirements.txt            # Зависимости
├── pyproject.toml              # Python проект конфиг
├── pytest.ini                  # Конфиг тестов
└── README.md
```

## Технологический стек

| Компонент | Технология | Назначение |
|-----------|-----------|-----------|
| **Framework** | FastAPI 0.110+ | REST API, автоматическая валидация |
| **БД** | PostgreSQL 15+ | Хранение данных |
| **ORM** | SQLAlchemy 2.0+ | Работа с БД |
| **Валидация** | Pydantic v2 | Валидация request/response |
| **Auth** | PyJWT + passlib | JWT токены, хеширование паролей |
| **Миграции** | Alembic 1.13+ | Версионирование БД |
| **Тестирование** | pytest + httpx | Unit + интеграционные тесты |
| **Логирование** | Python logging | Структурированные логи (JSON) |
| **ASGI** | Uvicorn | ASGI сервер |

## Основные классы и ответственность

### Models (ORM)

| Класс | Таблица | Ответственность |
|-------|--------|-----------------|
| `User` | users | email, пароль (хеш), роль (buyer/seller/admin), created_at |
| `Product` | products | название, описание, цена, category_id, seller_id (User), stock, created_at |
| `Category` | categories | название, parent_id (самоссылка для иерархии) |
| `Order` | orders | buyer_id (User), status (new/confirmed/sent/delivered), total, created_at |
| `OrderItem` | order_items | order_id, product_id, quantity, price_at_purchase |
| `Review` | reviews | product_id, author_id (User), rating (1-5), text, created_at |
| `WishlistItem` | wishlist_items | user_id, product_id, created_at |

### Services (Бизнес-логика)

| Класс | Методы | Примеры |
|-------|--------|---------|
| `UserService` | register, authenticate, get_profile, update_profile | JWT токен при логине |
| `ProductService` | create, update, delete, get_by_id, list, search, filter | Поиск по названию, фильтр по цене |
| `OrderService` | create_order, get_order, list_orders, update_status, cancel | Проверка наличия, блокировка stock |
| `ReviewService` | create_review, get_reviews, get_avg_rating | Только после покупки |
| `CartService` | add_item, remove_item, clear, get_cart | В памяти (Redis или session) |

### Routes (Эндпоинты)

```
POST   /auth/register          # Регистрация
POST   /auth/login             # Логин (JWT)

GET    /users/me               # Профиль текущего
PATCH  /users/me               # Обновить профиль

GET    /products               # Список (с поиском)
POST   /products               # Создать (только seller)
PATCH  /products/{id}          # Обновить (только автор)
DELETE /products/{id}          # Удалить (только автор)

POST   /cart                   # Добавить в корзину
GET    /cart                   # Получить корзину
DELETE /cart/{product_id}      # Удалить из корзины

POST   /orders                 # Создать заказ
GET    /orders                 # Мои заказы
GET    /orders/{id}            # Детали заказа
PATCH  /orders/{id}/status     # Обновить статус (только seller/admin)
PATCH  /orders/{id}/cancel     # Отменить (только buyer если не отправлен)

POST   /reviews                # Оставить отзыв
GET    /products/{id}/reviews  # Отзывы на товар

GET    /categories             # Список категорий
```

## Права доступа

| Операция | Buyer | Seller | Admin |
|----------|-------|--------|-------|
| Создать товар | ✗ | ✓ | ✓ |
| Создать заказ | ✓ | ✓ | ✓ |
| Обновить статус заказа | ✗ | ✓ (свой) | ✓ |
| Оставить отзыв | ✓ (после покупки) | ✓ (после покупки) | ✓ |
| Удалить товар | ✗ | ✓ (свой) | ✓ |