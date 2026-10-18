
from app.database.database import SessionLocal
from app.database.models import Queue, QueueEntry
from app.services.estimations import estimation_service


def test_estimate_is_zero_when_no_people_ahead():
    db = SessionLocal()
    try:
        result = estimation_service(
            db=db,
            queue_id=1,
            no_of_people_ahead=0,
        )
        assert result == 0
    finally:
        db.close()


def test_estimate_uses_default_when_no_history():
    db = SessionLocal()
    try:
        result = estimation_service(
            db=db,
            queue_id=1,
            no_of_people_ahead=2,
            default_service_time=10,
        )
        assert result == 20
    finally:
        db.close()



def test_estimate_uses_average_recorded_duration():
    from datetime import datetime, timedelta, timezone
    from app.database.database import SessionLocal
    from app.database.models import QueueEntry

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        entry = QueueEntry(
            queue_id=1,
            user_id=1,
            token_no="HIST001",
            status="served",
            service_started_at=now - timedelta(minutes=5),
            served_at=now,
        )
        db.add(entry)
        db.commit()

        result = estimation_service(
            db=db,
            queue_id=1,
            no_of_people_ahead=2,
        )

        assert result == 10
    finally:
        db.close()
