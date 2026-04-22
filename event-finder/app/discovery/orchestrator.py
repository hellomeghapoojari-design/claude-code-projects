"""Coordinates all discovery sources → dedup → score → upsert to DB."""
import datetime
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.event import Event
from app.models.scrape_run import ScrapeRun
from app.discovery.deduplicator import deduplicate, make_uid
from app.discovery.scorer import score_event, build_tags
from app.discovery.sources.base import RawEvent
from app.discovery.sources.ddgs_search import DDGSSearchSource
from app.discovery.sources.generic_scraper import scrape_page, make_session, STATIC_SEED_URLS
from app.discovery.sources.luma import LumaSource
from app.discovery.sources.eventbrite import EventbriteSource
from app.discovery.sources.meetup import MeetupSource
from app.discovery.ai.discovery_agent import AIDiscoveryAgent

MAX_SCRAPE_URLS = 40


def run_discovery(db: Session, run_type: str = "manual") -> dict:
    settings = get_settings()
    run = ScrapeRun(run_type=run_type, started_at=datetime.datetime.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    errors: list[str] = []
    all_raw: list[RawEvent] = []

    # 1. DDGS search → stub RawEvents (URLs to scrape)
    print("[Discovery] Running DDGS searches...")
    try:
        ddgs_stubs = DDGSSearchSource().fetch()
        print(f"  Found {len(ddgs_stubs)} URLs from search")
    except Exception as e:
        errors.append(f"DDGS: {e}")
        ddgs_stubs = []

    # 2. Scrape each URL from DDGS + seed URLs
    session = make_session()
    seen_urls: set[str] = set()
    urls_to_scrape = [ev.url for ev in ddgs_stubs if ev.url]
    for seed in STATIC_SEED_URLS:
        if seed not in seen_urls:
            urls_to_scrape.append(seed)

    print(f"[Discovery] Scraping {min(len(urls_to_scrape), MAX_SCRAPE_URLS)} URLs...")
    for url in urls_to_scrape[:MAX_SCRAPE_URLS]:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            ev = scrape_page(url, session)
            if ev:
                ev.source = ev.source or "generic"
                all_raw.append(ev)
        except Exception as e:
            errors.append(f"scrape {url[:50]}: {e}")

    # 3. Luma
    print("[Discovery] Fetching Luma events...")
    try:
        luma_events = LumaSource().fetch()
        all_raw.extend(luma_events)
        print(f"  Got {len(luma_events)} Luma events")
    except Exception as e:
        errors.append(f"Luma: {e}")

    # 4. Eventbrite
    if settings.eventbrite_token:
        print("[Discovery] Fetching Eventbrite events...")
        try:
            eb_events = EventbriteSource(settings.eventbrite_token).fetch()
            all_raw.extend(eb_events)
            print(f"  Got {len(eb_events)} Eventbrite events")
        except Exception as e:
            errors.append(f"Eventbrite: {e}")

    # 5. Meetup
    print("[Discovery] Fetching Meetup events...")
    try:
        meetup_events = MeetupSource(settings.meetup_token).fetch()
        all_raw.extend(meetup_events)
        print(f"  Got {len(meetup_events)} Meetup events")
    except Exception as e:
        errors.append(f"Meetup: {e}")

    # 6. AI Discovery
    if settings.anthropic_api_key:
        print("[Discovery] Running AI discovery...")
        try:
            ai_events = AIDiscoveryAgent(settings.anthropic_api_key).fetch()
            all_raw.extend(ai_events)
        except Exception as e:
            errors.append(f"AI Discovery: {e}")

    print(f"[Discovery] Total raw events before dedup: {len(all_raw)}")

    # Dedup
    unique = deduplicate(all_raw)
    print(f"[Discovery] After dedup: {len(unique)}")

    # Score + upsert
    new_count = 0
    updated_count = 0
    for raw in unique:
        if not raw.name or len(raw.name) < 4:
            continue
        if not raw.uid:
            raw.uid = make_uid(raw.url or raw.name)

        score, breakdown = score_event(raw)
        tags = build_tags(raw)

        existing = db.query(Event).filter(Event.uid == raw.uid).first()
        if existing:
            existing.score = score
            existing.score_breakdown = breakdown
            if not existing.relevance_tags:
                existing.relevance_tags = tags
            existing.last_scraped_at = datetime.datetime.utcnow()
            updated_count += 1
        else:
            ev = Event(
                uid=raw.uid,
                name=raw.name,
                event_type=raw.event_type,
                date_raw=raw.date_raw,
                date_start=raw.date_start,
                date_end=raw.date_end,
                location_city=raw.location_city,
                location_state=raw.location_state,
                is_virtual=raw.is_virtual,
                is_hybrid=raw.is_hybrid,
                organizer=raw.organizer,
                audience_size=raw.audience_size,
                description=raw.description,
                url=raw.url,
                contact_email=raw.contact_email,
                contact_url=raw.contact_url,
                source=raw.source,
                source_domain=raw.source_domain,
                score=score,
                score_breakdown=breakdown,
                has_speaking=raw.has_speaking,
                has_partnership=raw.has_partnership,
                relevance_tags=tags,
                last_scraped_at=datetime.datetime.utcnow(),
            )
            db.add(ev)
            new_count += 1

    db.commit()

    run.finished_at = datetime.datetime.utcnow()
    run.events_found = len(unique)
    run.events_new = new_count
    run.events_updated = updated_count
    run.error_log = "\n".join(errors)
    run.status = "completed"
    db.commit()

    result = {
        "run_id": run.id,
        "events_found": len(unique),
        "events_new": new_count,
        "events_updated": updated_count,
        "errors": errors,
    }
    print(f"[Discovery] Done — {new_count} new, {updated_count} updated")
    return result
