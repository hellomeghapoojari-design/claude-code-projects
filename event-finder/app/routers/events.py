from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventOut, EventUpdate, EventCreate
from app.discovery.deduplicator import make_uid
from app.discovery.scorer import score_event, build_tags
from app.discovery.sources.generic_scraper import parse_date
from app.discovery.sources.base import RawEvent

router = APIRouter(prefix="/api/events", tags=["events"])

VALID_STATUSES = {"new", "interested", "applied", "confirmed", "rejected", "passed"}


@router.get("", response_model=list[EventOut])
def list_events(
    city: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    shortlisted: Optional[bool] = Query(None),
    has_speaking: Optional[bool] = Query(None),
    min_score: int = Query(0),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    sort_by: str = Query("score"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    q = db.query(Event).filter(Event.score >= min_score)

    if city:
        q = q.filter(Event.location_city.ilike(f"%{city}%"))
    if event_type:
        q = q.filter(Event.event_type.ilike(f"%{event_type}%"))
    if status:
        q = q.filter(Event.status == status)
    if source:
        q = q.filter(Event.source == source)
    if shortlisted is not None:
        q = q.filter(Event.shortlisted == shortlisted)
    if has_speaking is not None:
        q = q.filter(Event.has_speaking == has_speaking)
    if date_from:
        q = q.filter(or_(Event.date_start >= date_from, Event.date_start == None))  # noqa: E711
    if date_to:
        q = q.filter(or_(Event.date_start <= date_to, Event.date_start == None))  # noqa: E711

    if sort_by == "date":
        q = q.order_by(Event.date_start.asc().nullslast())
    elif sort_by == "name":
        q = q.order_by(Event.name.asc())
    else:
        q = q.order_by(Event.score.desc(), Event.date_start.asc().nullslast())

    return q.offset(offset).limit(limit).all()


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.patch("/{event_id}", response_model=EventOut)
def update_event(event_id: int, payload: EventUpdate, db: Session = Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
        ev.status = payload.status
    if payload.shortlisted is not None:
        ev.shortlisted = payload.shortlisted
    if payload.notes is not None:
        ev.notes = payload.notes
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/manual", response_model=EventOut, status_code=201)
def create_manual_event(payload: EventCreate, db: Session = Depends(get_db)):
    import hashlib
    uid = make_uid(payload.url or payload.name)
    existing = db.query(Event).filter(Event.uid == uid).first()
    if existing:
        raise HTTPException(status_code=409, detail="Event already exists")

    raw = RawEvent(
        uid=uid,
        name=payload.name,
        event_type=payload.event_type,
        date_raw=payload.date_raw,
        date_start=payload.date_start or parse_date(payload.date_raw),
        date_end=payload.date_end,
        location_city=payload.location_city,
        location_state=payload.location_state,
        is_virtual=payload.is_virtual,
        is_hybrid=payload.is_hybrid,
        organizer=payload.organizer,
        description=payload.description,
        url=payload.url,
        contact_email=payload.contact_email,
        contact_url=payload.contact_url,
        source="manual",
    )
    sc, breakdown = score_event(raw)
    tags = build_tags(raw)

    ev = Event(
        uid=uid,
        name=payload.name,
        event_type=payload.event_type,
        date_raw=payload.date_raw,
        date_start=raw.date_start,
        date_end=payload.date_end,
        location_city=payload.location_city,
        location_state=payload.location_state,
        is_virtual=payload.is_virtual,
        is_hybrid=payload.is_hybrid,
        organizer=payload.organizer,
        description=payload.description,
        url=payload.url,
        contact_email=payload.contact_email,
        contact_url=payload.contact_url,
        source="manual",
        score=sc,
        score_breakdown=breakdown,
        relevance_tags=tags,
        notes=payload.notes,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
