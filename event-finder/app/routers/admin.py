import threading
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.scrape_run import ScrapeRun

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _run_in_thread(run_type: str):
    db = SessionLocal()
    try:
        from app.discovery.orchestrator import run_discovery
        run_discovery(db, run_type=run_type)
    except Exception as e:
        print(f"[Admin] Discovery error: {e}")
    finally:
        db.close()


@router.post("/run-discovery")
def trigger_discovery(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_in_thread, "manual")
    return {"message": "Discovery started in background"}


@router.post("/run-ai-discovery")
def trigger_ai_discovery(background_tasks: BackgroundTasks):
    def _ai_only():
        db = SessionLocal()
        try:
            from app.config import get_settings
            from app.discovery.ai.discovery_agent import AIDiscoveryAgent
            from app.discovery.orchestrator import run_discovery
            run_discovery(db, run_type="ai_discovery")
        except Exception as e:
            print(f"[Admin] AI discovery error: {e}")
        finally:
            db.close()

    background_tasks.add_task(_ai_only)
    return {"message": "AI discovery started in background"}


@router.post("/rescore")
def trigger_rescore(background_tasks: BackgroundTasks):
    def _rescore():
        db = SessionLocal()
        try:
            from app.config import get_settings
            from app.discovery.ai.relevance_scorer import RelevanceScorer
            settings = get_settings()
            scorer = RelevanceScorer(settings.anthropic_api_key)
            total = 0
            while True:
                n = scorer.score_pending(db, batch_size=10)
                if n == 0:
                    break
                total += n
            print(f"[Rescore] Updated {total} events")
        except Exception as e:
            print(f"[Admin] Rescore error: {e}")
        finally:
            db.close()

    background_tasks.add_task(_rescore)
    return {"message": "Rescoring started in background"}


@router.get("/runs")
def list_runs(limit: int = 20, db: Session = Depends(get_db)):
    runs = (
        db.query(ScrapeRun)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "run_type": r.run_type,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "events_found": r.events_found,
            "events_new": r.events_new,
            "events_updated": r.events_updated,
            "has_errors": bool(r.error_log),
        }
        for r in runs
    ]


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    from app.models.event import Event
    total = db.query(Event).count()
    shortlisted = db.query(Event).filter(Event.shortlisted == True).count()  # noqa: E712
    applied = db.query(Event).filter(Event.status == "applied").count()
    confirmed = db.query(Event).filter(Event.status == "confirmed").count()
    speaking = db.query(Event).filter(Event.has_speaking == True).count()  # noqa: E712
    high = db.query(Event).filter(Event.score >= 8).count()
    return {
        "total": total,
        "shortlisted": shortlisted,
        "applied": applied,
        "confirmed": confirmed,
        "has_speaking": speaking,
        "high_priority": high,
    }
