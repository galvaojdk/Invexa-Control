import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

from app.models.user import User
from app.api.dependencies import get_db, login_required

# ... (previous imports remain same, just ensuring correct context)

@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def client(db_session, test_user):
    """Create a TestClient with overridden dependencies."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    def override_login_required():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[login_required] = override_login_required
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()
