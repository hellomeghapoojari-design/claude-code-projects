"""Luma event scraper — ported from agent.py and extended."""
import json
import hashlib
import re
import time
import random
from typing import Optional, List
import requests
from app.discovery.sources.base import BaseSource, RawEvent
from app.discovery.sources.generic_scraper import (
    make_session, safe_get, clean_text, parse_date, domain_of, _detect_city
)

LUMA_INDIA_SEARCHES = [
    "https://lu.ma/discover?tag=leadership&location=India",
    "https://lu.ma/discover?tag=team-building&location=India",
    "https://lu.ma/discover?tag=corporate&location=India",
    "https://lu.ma/discover?tag=motivation&location=India",
]


class LumaSource(BaseSource):
    def fetch(self) -> list[RawEvent]:
        events: list[RawEvent] = []
        session = make_session()

        # Try Luma's public API endpoint
        try:
            resp = requests.get(
                "https://api.lu.ma/public/v1/calendar/list-events",
                params={"pagination_limit": 50},
                timeout=10,
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("entries", []):
                    ev_data = item.get("event", item)
                    ev = self._parse_api_event(ev_data)
                    if ev:
                        events.append(ev)
        except Exception as e:
            print(f"  [Luma API] {e}")

        # Scrape discover pages
        for url in LUMA_INDIA_SEARCHES:
            soup = safe_get(session, url)
            if not soup:
                continue
            for a in soup.find_all("a", href=re.compile(r"lu\.ma/", re.I)):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://lu.ma" + href
                ev = self._scrape_event_page(href, session)
                if ev:
                    events.append(ev)
            time.sleep(random.uniform(2, 4))

        return events

    def _parse_api_event(self, data: dict) -> Optional[RawEvent]:
        name = data.get("name", "")
        if not name or len(name) < 4:
            return None
        url = f"https://lu.ma/{data.get('url', data.get('slug', ''))}"
        geo = data.get("geo_address_info", {}) or {}
        return RawEvent(
            uid=hashlib.md5(url.encode()).hexdigest(),
            name=name,
            date_raw=data.get("start_at", ""),
            date_start=parse_date(data.get("start_at", "")),
            location_city=geo.get("city", "") or geo.get("description", ""),
            is_virtual=data.get("is_virtual", False),
            organizer=(data.get("hosts") or [{}])[0].get("name", "") if data.get("hosts") else "",
            description=clean_text(data.get("description", "")),
            url=url,
            source="luma",
            source_domain="lu.ma",
        )

    def _scrape_event_page(self, url: str, session) -> Optional[RawEvent]:
        soup = safe_get(session, url)
        if not soup:
            return None
        try:
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                page_data = json.loads(script.string)
                ep = page_data.get("props", {}).get("pageProps", {}).get("event", {})
                if ep:
                    geo = ep.get("geo_address_info", {}) or {}
                    hosts = ep.get("hosts", [])
                    name = ep.get("name", "")
                    if not name or len(name) < 4:
                        return None
                    return RawEvent(
                        uid=hashlib.md5(url.encode()).hexdigest(),
                        name=name,
                        date_raw=ep.get("start_at", ""),
                        date_start=parse_date(ep.get("start_at", "")),
                        location_city=geo.get("city", "") or geo.get("description", ""),
                        organizer=hosts[0].get("name", "") if hosts and isinstance(hosts[0], dict) else "",
                        description=clean_text(ep.get("description", "")),
                        url=url,
                        source="luma",
                        source_domain="lu.ma",
                    )
        except Exception:
            pass
        # Fallback: generic scrape
        title = soup.find("title")
        name = clean_text(title.get_text() if title else "", 200)
        if not name or len(name) < 4:
            return None
        return RawEvent(
            uid=hashlib.md5(url.encode()).hexdigest(),
            name=name,
            url=url,
            source="luma",
            source_domain="lu.ma",
        )
