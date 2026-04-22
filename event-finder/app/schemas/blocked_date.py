from datetime import date, datetime
from pydantic import BaseModel


class BlockedDateCreate(BaseModel):
    date_start: date
    date_end: date
    reason: str = ""


class BlockedDateOut(BaseModel):
    id: int
    date_start: date
    date_end: date
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
