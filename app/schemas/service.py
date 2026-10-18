from pydantic import BaseModel,EmailStr, ConfigDict

class ServiceIn(BaseModel):
    name: str
    description: str | None = None

class ServiceOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    user_id: int
    model_config = ConfigDict(from_attributes=True)