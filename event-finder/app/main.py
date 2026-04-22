from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.database import create_tables
from app.routers import events, calendar, admin
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    _check_env(settings)
    create_tables()

    from app.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    # Shutdown
    from app.scheduler import stop_scheduler
    stop_scheduler()


def _check_env(settings):
    if not settings.anthropic_api_key:
        print("[WARN] ANTHROPIC_API_KEY not set — AI discovery and scoring disabled")
    if not settings.eventbrite_token:
        print("[INFO] EVENTBRITE_TOKEN not set — Eventbrite source disabled")
    if not settings.meetup_token:
        print("[INFO] MEETUP_TOKEN not set — Meetup will attempt unauthenticated queries")


app = FastAPI(
    title="Event Finder",
    description="Personal event discovery tool for Indian corporate/motivational speaker",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(events.router)
app.include_router(calendar.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend as static files — must be last
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{path:path}")
    def serve_spa(path: str):
        file_path = os.path.join(frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))
