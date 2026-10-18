
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import QueueEntry


def estimation_service(
    db: Session,
    queue_id: int,
    no_of_people_ahead: int,
    default_service_time: int = 10,
) -> int:
    if no_of_people_ahead <= 0:
        return 0

    avg_time = (
        db.query(
            func.avg(
                func.extract(
                    "epoch",
                    QueueEntry.served_at - QueueEntry.service_started_at,
                ) / 60
            )
        )
        .filter(
            QueueEntry.queue_id == queue_id,
            QueueEntry.status == "served",
            QueueEntry.served_at.isnot(None),
            QueueEntry.service_started_at.isnot(None),
        )
        .scalar()
    )

    if avg_time is None or avg_time <= 0:
        avg_time = default_service_time

    return max(0, round(no_of_people_ahead * avg_time))
