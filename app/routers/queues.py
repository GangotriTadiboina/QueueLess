from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Queue, QueueEntry, Service,User
from app.schemas.queue import queueIn, queueOut,queueEntryIn, queueEntryOut, queueStatusOut
from app.core.security import get_current_user
from datetime import datetime, timedelta, timezone
from app.services.queue_services import get_user_queue_status
from app.services.estimations import estimation_service
from fastapi import WebSocket, WebSocketDisconnect
from app.websocket.manager import manager

router=APIRouter(
    prefix="/queues",
    tags=["Queues"]
)

def staff_or_admin(user:User):
    if user.role not in ["staff","admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff or admin have permission to perform this action"
        )

@router.post("/", response_model=queueOut)
def create_queue(queue: queueIn,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    staff_or_admin(current_user)
    service = db.query(Service).filter(
        Service.id == queue.service_id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    new_queue = Queue(
        service_id=queue.service_id,
        status="active",
        current=0,
    )

    db.add(new_queue)
    db.commit()
    db.refresh(new_queue)
    return new_queue

@router.get("/",response_model=list[queueOut])
def get_queues(db:Session=Depends(get_db)):
    queues=db.query(Queue).all()
    return queues

@router.get("/{queue_id}/status", response_model=queueStatusOut)
def get_queue_status(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = get_user_queue_status(
        db, current_user.id, queue_id
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="You have not joined in this queue"
        )

    result["estimated_waiting_time"] = estimation_service(
        db=db,
        queue_id=queue_id,
        no_of_people_ahead=result["no_of_people_ahead"],
    )

    return result

@router.get("/{queue_id}",response_model=queueOut)
def get_queue(queue_id: int, db:Session=Depends(get_db)):
    queue=db.query(Queue).filter(Queue.id==queue_id).first()
    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Queue not found"
        )
    return queue


@router.post("/{queue_id}/join", response_model=queueEntryOut)
async def join_queue(
    queue_id: int,
    entry: queueEntryIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # Lock this queue row until the transaction finishes.
        queue = (
            db.query(Queue)
            .filter(Queue.id == queue_id)
            .with_for_update()
            .first()
        )

        if not queue:
            raise HTTPException(
                status_code=404,
                detail="Queue not found"
            )

        if queue.status != "active":
            raise HTTPException(
            status_code=400,
            detail="Queue is not active"
        )

        # Generate the next token while holding the lock.
        next_no = queue.current + 1
        token_no = f"A{next_no:03d}"

        new_entry = QueueEntry(
            queue_id=queue_id,
            user_id=current_user.id,
            token_no=token_no,
            status="waiting"
        )

        queue.current = next_no
        db.add(new_entry)

        # Save the counter and entry together.
        db.commit()
        db.refresh(new_entry)

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        import logging
        logging.exception("Error while joining queue")
        raise HTTPException(
            status_code=500,
            detail="Could not join queue"
        )

    # Broadcast only after the database commit succeeds.
    await manager.broadcast(
        queue_id,
        {
            "event": "Customer joined in queue",
            "token_no": new_entry.token_no,
            "status": new_entry.status
        }
    )

    return new_entry



@router.post("/{queue_id}/serve", response_model=queueEntryOut)
async def serve_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    staff_or_admin(current_user)

    try:
        queue = (
            db.query(Queue)
            .filter(Queue.id == queue_id)
            .with_for_update()
            .first()
        )

        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")

        if queue.status != "active":
            raise HTTPException(status_code=400, detail="Queue is not active")

        # Don't start another customer while one is already being served.
        current_service = db.query(QueueEntry).filter(
            QueueEntry.queue_id == queue_id,
            QueueEntry.status == "serving",
        ).first()

        if current_service:
            raise HTTPException(
                status_code=409,
                detail="A customer is already being served"
            )

        entry = (
            db.query(QueueEntry)
            .filter(
                QueueEntry.queue_id == queue_id,
                QueueEntry.status == "waiting",
            )
            .order_by(QueueEntry.id.asc())
            .with_for_update()
            .first()
        )
        if not entry:
            raise HTTPException(
                status_code=404,
                detail="No waiting entries in the queue"
        )
        entry.status = "serving"
        entry.service_started_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(entry)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not start service"
        )

    await manager.broadcast(
        queue_id,
        {
            "event": "Service started",
            "token_no": entry.token_no,
            "status": entry.status,
        },
    )

    return entry


@router.post("/{queue_id}/finish", response_model=queueEntryOut)
async def finish_service(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    staff_or_admin(current_user)

    entry = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.queue_id == queue_id,
            QueueEntry.status == "serving",
        )
        .order_by(QueueEntry.id.asc())
        .with_for_update()
        .first()
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="No customer is currently being served"
        )

    entry.status = "served"
    entry.served_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(entry)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not finish service"
        )

    await manager.broadcast(
        queue_id,
        {
            "event": "Service completed",
            "token_no": entry.token_no,
            "status": entry.status,
        },
    )

    return entry


@router.get("/{queue_id}/entries", response_model=list[queueEntryOut])
def get_queue_entries(queue_id: int,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    staff_or_admin(current_user)
    queue = db.query(Queue).filter(
        Queue.id == queue_id
    ).first()
    if not queue:
        raise HTTPException(
            status_code=404,
            detail="Queue not found",
        )

    return db.query(QueueEntry).filter(QueueEntry.queue_id == queue_id).all()

@router.websocket("/{queue_id}/live")
async def websocket_endpoint(
    websocket: WebSocket,
    queue_id: int,
):
    await manager.connect(queue_id, websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(queue_id, websocket)