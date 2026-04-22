from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.blocked_date import BlockedDate
from app.models.event import Event
from app.schemas.blocked_date import BlockedDateCreate, BlockedDateOut

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _is_blocked(event_date: Optional[date], blocks: list[BlockedDate]) -> bool:
    if not event_date:
        return False
    return any(b.date_start <= event_date <= b.date_end for b in blocks)


@router.get("/blocked-dates", response_model=list[BlockedDateOut])
def list_blocked_dates(db: Session = Depends(get_db)):
    return db.query(BlockedDate).order_by(BlockedDate.date_start.asc()).all()


@router.post("/blocked-dates", response_model=BlockedDateOut, status_code=201)
def create_blocked_date(payload: BlockedDateCreate, db: Session = Depends(get_db)):
    if payload.date_end < payload.date_start:
        raise HTTPException(status_code=422, detail="date_end must be >= date_start")
    bd = BlockedDate(date_start=payload.date_start, date_end=payload.date_end, reason=payload.reason)
    db.add(bd)
    db.commit()
    db.refresh(bd)
    return bd


@router.delete("/blocked-dates/{block_id}", status_code=204)
def delete_blocked_date(block_id: int, db: Session = Depends(get_db)):
    bd = db.query(BlockedDate).filter(BlockedDate.id == block_id).first()
    if not bd:
        raise HTTPException(status_code=404, detail="Blocked date not found")
    db.delete(bd)
    db.commit()


@router.get("/events")
def events_for_month(month: str, db: Session = Depends(get_db)):
    """Return events for a month (YYYY-MM) with conflict flags."""
    try:
        year, mon = int(month[:4]), int(month[5:7])
        month_start = date(year, mon, 1)
        import calendar as cal
        last_day = cal.monthrange(year, mon)[1]
        month_end = date(year, mon, last_day)
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM format")

    from sqlalchemy import or_
    events = (
        db.query(Event)
        .filter(
            or_(
                (Event.date_start >= month_start) & (Event.date_start <= month_end),
                Event.date_start == None,  # noqa: E711
            )
        )
        .order_by(Event.date_start.asc().nullslast())
        .all()
    )

    blocks = db.query(BlockedDate).filter(
        BlockedDate.date_start <= month_end,
        BlockedDate.date_end >= month_start,
    ).all()

    result = []
    for ev in events:
        result.append({
            "id": ev.id,
            "name": ev.name,
            "date_start": ev.date_start.isoformat() if ev.date_start else None,
            "location_city": ev.location_city,
            "score": ev.score,
            "status": ev.status,
            "shortlisted": ev.shortlisted,
            "has_speaking": ev.has_speaking,
            "conflict": _is_blocked(ev.date_start, blocks),
        })

    return {
        "month": month,
        "events": result,
        "blocked_dates": [
            {"id": b.id, "date_start": b.date_start.isoformat(),
             "date_end": b.date_end.isoformat(), "reason": b.reason}
            for b in blocks
        ],
    }
