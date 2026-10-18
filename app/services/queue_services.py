
from sqlalchemy.orm import Session

from app.database.models import QueueEntry


def get_user_queue_status(db: Session,user_id: int,queue_id: int):
    user_entry = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.user_id == user_id,
            QueueEntry.queue_id == queue_id,
        )
        .order_by(QueueEntry.id.desc())
        .first()
    )

    if user_entry is None:
        return None

    if user_entry.status == "served":
        return {
            "status": "Served",
            "token_no": user_entry.token_no,
            "position": 0,
            "no_of_people_ahead": 0,
        }

    if user_entry.status != "waiting":
        return {
            "status": user_entry.status,
            "token_no": user_entry.token_no,
            "position": 0,
            "no_of_people_ahead": 0,
        }
    no_of_people_ahead = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == queue_id,
            QueueEntry.status == "waiting",
            QueueEntry.id < user_entry.id,
        )
        .count()
    )
    return {
        "status": "waiting",
        "token_no": user_entry.token_no,
        "position": no_of_people_ahead + 1,
        "no_of_people_ahead": no_of_people_ahead,
    }
