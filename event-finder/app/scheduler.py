"""APScheduler setup: weekly full discovery + daily rescore."""
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: Optional[BackgroundScheduler] = None


def _weekly_discovery():
    from app.database import SessionLocal
    from app.discovery.orchestrator import run_discovery
    db = SessionLocal()
    try:
        print("[Scheduler] Starting weekly discovery run...")
        run_discovery(db, run_type="scheduled")
    except Exception as e:
        print(f"[Scheduler] Weekly discovery failed: {e}")
    finally:
        db.close()


def _daily_rescore():
    from app.database import SessionLocal
    from app.config import get_settings
    from app.discovery.ai.relevance_scorer import RelevanceScorer
    settings = get_settings()
    if not settings.anthropic_api_key:
        return
    db = SessionLocal()
    try:
        scorer = RelevanceScorer(settings.anthropic_api_key)
        total = 0
        while True:
            n = scorer.score_pending(db, batch_size=10)
            if n == 0:
                break
            total += n
        if total:
            print(f"[Scheduler] Rescored {total} events")
    except Exception as e:
        print(f"[Scheduler] Daily rescore failed: {e}")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(_weekly_discovery, CronTrigger(day_of_week="mon", hour=3, minute=0))
    _scheduler.add_job(_daily_rescore, CronTrigger(hour=6, minute=0))
    _scheduler.start()
    print("[Scheduler] Started — weekly discovery Monday 3 AM IST, daily rescore 6 AM IST")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
