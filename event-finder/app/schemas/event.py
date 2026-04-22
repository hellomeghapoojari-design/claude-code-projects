from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class EventOut(BaseModel):
    id: int
    uid: str
    name: str
    event_type: str
    date_raw: str
    date_start: Optional[date]
    date_end: Optional[date]
    location_city: str
    location_state: str
    is_virtual: bool
    is_hybrid: bool
    organizer: str
    audience_size: Optional[int]
    description: str
    url: str
    contact_email: str
    contact_url: str
    source: str
    score: int
    score_breakdown: Optional[dict]
    has_speaking: bool
    has_partnership: bool
    relevance_tags: Optional[list]
    status: str
    shortlisted: bool
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventUpdate(BaseModel):
    status: Optional[str] = None
    shortlisted: Optional[bool] = None
    notes: Optional[str] = None


class EventCreate(BaseModel):
    name: str
    event_type: str = ""
    date_raw: str = ""
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    location_city: str = ""
    location_state: str = ""
    is_virtual: bool = False
    is_hybrid: bool = False
    organizer: str = ""
    description: str = ""
    url: str = ""
    contact_email: str = ""
    contact_url: str = ""
    notes: str = ""
