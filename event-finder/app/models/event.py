from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, Date, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), default="")
    date_raw: Mapped[str] = mapped_column(String(200), default="")
    date_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    date_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location_city: Mapped[str] = mapped_column(String(100), default="")
    location_state: Mapped[str] = mapped_column(String(100), default="")
    is_virtual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hybrid: Mapped[bool] = mapped_column(Boolean, default=False)
    organizer: Mapped[str] = mapped_column(String(200), default="")
    audience_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(2000), default="")
    contact_email: Mapped[str] = mapped_column(String(300), default="")
    contact_url: Mapped[str] = mapped_column(String(2000), default="")
    source: Mapped[str] = mapped_column(String(50), default="", index=True)
    source_domain: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    has_speaking: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_partnership: Mapped[bool] = mapped_column(Boolean, default=False)
    relevance_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
