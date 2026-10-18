from pydantic import BaseModel,EmailStr, ConfigDict
from datetime import datetime

class queueIn(BaseModel):
   service_id: int

class queueOut(BaseModel):
    id: int
    service_id: int
    status: str
    current: int
    model_config = ConfigDict(from_attributes=True)

class queueEntryIn(BaseModel):
    pass

class queueEntryOut(BaseModel):
    id: int
    queue_id: int
    user_id: int
    token_no: str
    status: str
    joined_at: datetime | None = None
    service_started_at: datetime | None = None
    served_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class queueStatusOut(BaseModel):
    status: str
    token_no: str
    position: int
    no_of_people_ahead: int
    estimated_waiting_time:int    
    model_config = ConfigDict(from_attributes=True)
