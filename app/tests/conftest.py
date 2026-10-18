
import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables from the main QueueLess/.env file.
load_dotenv()

# Read the dedicated test database URL.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is missing from the .env file"
    )

# Prevent tests from running against the development database.
if not TEST_DATABASE_URL.rstrip("/").endswith("/fastapi_test"):
    raise RuntimeError(
        "Tests must use the fastapi_test database"
    )

# Set this before importing the application database module.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database.database import Base
from app.database import models
from app.core.security import hash_password


# Use a dedicated engine for the test database.
test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(autouse=True)
def setup_test_database():
    # Create tables if they do not exist.
    Base.metadata.create_all(bind=test_engine)

    # Clear test data before every test.
    with test_engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                "queue_entries, queues, services, users "
                "RESTART IDENTITY CASCADE"
            )
        )

    db = TestingSessionLocal()

    try:
        # Create a test user.
        user = models.User(
            name="Test User",
            email="gangotri2@example.com",
            password=hash_password("TestPassword123!"),
            is_active=True,
            role="customer",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create a service owned by the test user.
        service = models.Service(
            name="Test Service",
            description="Service for automated tests",
            is_active=True,
            user_id=user.id,
        )
        db.add(service)
        db.commit()
        db.refresh(service)

        # Create an active queue for that service.
        queue = models.Queue(
            service_id=service.id,
            status="active",
            current=0,
        )
        db.add(queue)
        db.commit()

        yield

    finally:
        db.close()
