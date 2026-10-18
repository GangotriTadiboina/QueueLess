from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from .database import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,unique=True,index=True)
    name=Column(String,nullable=False)
    email=Column(String,nullable=False,unique=True,index=True)
    password=Column(String,nullable=False)
    is_active=Column(Boolean,default=True)
    role=Column(String,nullable=False,default="customer")

class Service(Base):
    __tablename__="services"
    id=Column(Integer,primary_key=True,unique=True,index=True)
    name=Column(String,nullable=False)
    description=Column(String,nullable=False)
    is_active=Column(Boolean,default=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)

class Queue(Base):
    __tablename__="queues"
    id=Column(Integer,primary_key=True,unique=True,index=True)
    service_id=Column(Integer,ForeignKey("services.id"),nullable=False)
    status=Column(String,default="active",nullable=False)
    current=Column(Integer,nullable=False,default=0)




class QueueEntry(Base):
    __tablename__ = "queue_entries"

    __table_args__ = (
        UniqueConstraint(
            "queue_id",
            "token_no",
            name="uq_queue_entry_token"
        ),
    )

    id = Column(Integer, primary_key=True, unique=True, index=True)
    queue_id = Column(Integer, ForeignKey("queues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_no = Column(String(20), nullable=False)
    status = Column(String, nullable=False)

    joined_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    service_started_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)
