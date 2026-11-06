from typing import Literal
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["customer", "staff"] = "customer"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    role: str

    model_config = ConfigDict(from_attributes=True)