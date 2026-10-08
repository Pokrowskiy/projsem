from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


client_ip_counter = count(1)


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    yield test_session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(database):
    def override_get_db():
        db = database()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client_ip = f"192.0.2.{next(client_ip_counter)}"
    with TestClient(app, client=(client_ip, 50000)) as test_client:
        yield test_client
    app.dependency_overrides.clear()
