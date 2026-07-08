import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, StaticPool
from app.models import User, UserRole
from app.db.base import Base
from app.main import app
from app.api.deps import get_database_session

@pytest.fixture(scope="function")
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    def override_get_database_session():
        yield db_session

    app.dependency_overrides[get_database_session] = override_get_database_session
    
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

def test_login_success(client: TestClient, db_session: Session):
    from app.core.rate_limit import limiter
    limiter.reset()
    from app.core.security import hash_password
    # Setup test user
    user = User(
        name="Test Auth User",
        email="auth_test@school.com",
        password_hash=hash_password("password123"),
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "auth_test@school.com", "password": "password123"},
        headers={"X-Forwarded-For": "1.1.1.1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    from app.core.rate_limit import limiter
    limiter.reset()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@school.com", "password": "wrongpassword"},
        headers={"X-Forwarded-For": "2.2.2.2"}
    )
    assert response.status_code == 401

def test_me_endpoint(client: TestClient, db_session: Session):
    from app.core.security import hash_password, create_access_token
    user = User(
        name="Me Test",
        email="me@school.com",
        password_hash=hash_password("pass"),
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.commit()
    
    token = create_access_token(str(user.id))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@school.com"
