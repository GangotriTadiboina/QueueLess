
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.database.database import SessionLocal
from app.database.models import Queue, User, QueueEntry
client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Queue Management System is running!"
    }


def test_unknown_route():
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404


def test_queue_status_without_token():
    response = client.get("/queues/1/status")
    assert response.status_code == 401


def test_join_queue_without_token():
    response = client.post("/queues/1/join")
    assert response.status_code == 401


def test_login_with_invalid_credentials():
    response = client.post(
        "/auth/login",
        data={
            "username": "wrong@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401

def test_login_with_valid_credentials():
    response = client.post(
        "/auth/login",
        data={
            "username": "gangotri2@example.com",
            "password": "TestPassword123!"
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"



def test_queue_status_with_valid_token():
    login_response = client.post(
        "/auth/login",
        data={
            "username": "gangotri2@example.com",
            "password": "TestPassword123!"
        }
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Join the queue
    join_response = client.post(
        "/queues/1/join",
        headers=headers,
        json={}
    )

    assert join_response.status_code in (200, 201), (
        f"Join failed: {join_response.status_code} "
        f"{join_response.text}"
    )

    # Check queue status
    response = client.get(
        "/queues/1/status",
        headers=headers
    )

    assert response.status_code == 200, (
        f"Status failed: {response.status_code} "
        f"{response.text}"
    )

    login_response = client.post(
        "/auth/login",
        data={
            "username": "gangotri2@example.com",
            "password": "TestPassword123!"
        }
    )

    response = client.post(
        "/queues/99999/join",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Queue not found"


def test_join_queue_without_body_fields():
    login_response = client.post(
        "/auth/login",
        data={
            "username": "gangotri2@example.com",
            "password": "TestPassword123!"
        }
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/queues/1/join",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )

    assert response.status_code in (200, 201)


def test_queue_status_for_user_who_has_not_joined():
    login_response = client.post(
        "/auth/login",
        data={
            "username": "gangotri2@example.com",
            "password": "TestPassword123!"
        }
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/queues/99999/status",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code in (404, 400)


def get_test_token():
    response = client.post(
        "/auth/login",
        data={
            "username": "gangotri2@example.com",
            "password": "TestPassword123!"
        }
    )

    assert response.status_code == 200, response.text
    return response.json()["access_token"]

def test_tokens_are_generated_sequentially():
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/queues/1/join", headers=headers, json={})
    second = client.post("/queues/1/join", headers=headers, json={})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["token_no"] == "A001"
    assert second.json()["token_no"] == "A002"


def test_inactive_queue_rejects_joining():
    db = SessionLocal()
    try:
        queue = db.query(Queue).filter(Queue.id == 1).first()
        assert queue is not None
        queue.status = "inactive"
        db.commit()
    finally:
        db.close()

    token = get_test_token()
    response = client.post(
        "/queues/1/join",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Queue is not active"


def test_queue_position_updates_correctly():
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/queues/1/join", headers=headers, json={})
    second = client.post("/queues/1/join", headers=headers, json={})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    response = client.get("/queues/1/status", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["token_no"] == "A002"
    assert data["position"] == 2
    assert data["no_of_people_ahead"] == 1


def test_staff_can_serve_next_customer():
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == "gangotri2@example.com"
        ).first()
        assert user is not None
        user.role = "staff"
        db.commit()
    finally:
        db.close()

    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Join the queue
    joined = client.post(
        "/queues/1/join",
        headers=headers,
        json={},
    )
    assert joined.status_code == 200, joined.text

    # Start serving the next customer
    started = client.post(
        "/queues/1/serve",
        headers=headers,
    )
    assert started.status_code == 200, started.text
    assert started.json()["token_no"] == "A001"
    assert started.json()["status"] == "serving"
    assert started.json()["service_started_at"] is not None

    # Finish serving the customer
    finished = client.post(
        "/queues/1/finish",
        headers=headers,
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["token_no"] == "A001"
    assert finished.json()["status"] == "served"
    assert finished.json()["served_at"] is not None


def test_serving_empty_queue_returns_404():
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == "gangotri2@example.com"
        ).first()
        assert user is not None
        user.role = "staff"
        db.commit()
    finally:
        db.close()

    token = get_test_token()
    response = client.post(
        "/queues/1/serve",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No waiting entries in the queue"



def test_duplicate_token_rejected():
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == "gangotri2@example.com"
        ).first()

        queue = db.query(Queue).filter(
            Queue.id == 1
        ).first()

        assert user is not None, "Test user was not created"
        assert queue is not None, "Test queue was not created"

        first_entry = QueueEntry(
            queue_id=queue.id,
            user_id=user.id,
            token_no="TEST999",
            status="waiting"
        )
        db.add(first_entry)
        db.commit()

        duplicate_entry = QueueEntry(
            queue_id=queue.id,
            user_id=user.id,
            token_no="TEST999",
            status="waiting"
        )
        db.add(duplicate_entry)

        try:
            db.commit()
            assert False, "Duplicate token should have been rejected"
        except IntegrityError:
            db.rollback()

    finally:
        db.close()
