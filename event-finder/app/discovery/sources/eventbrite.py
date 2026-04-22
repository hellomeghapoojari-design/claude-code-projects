"""Eventbrite API source."""
import hashlib
import time
from typing import Optional, List
import requests
from app.discovery.sources.base import BaseSource, RawEvent
from app.discovery.sources.generic_scraper import parse_date, clean_text

INDIA_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Noida", "Gurgaon",
]

SEARCH_TERMS = [
    "leadership team building",
    "corporate motivation workshop",
    "HR conference",
    "employee engagement",
    "organizational culture",
]

EVENTBRITE_BASE = "https://www.eventbriteapi.com/v3"


class EventbriteSource(BaseSource):
    def __init__(self, token: str):
        self.token = token

    def fetch(self) -> list[RawEvent]:
        if not self.token:
            print("  [Eventbrite] No token configured, skipping")
            return []

        events: list[RawEvent] = []
        headers = {"Authorization": f"Bearer {self.token}"}

        for city in INDIA_CITIES[:5]:
            for term in SEARCH_TERMS[:3]:
                try:
                    resp = requests.get(
                        f"{EVENTBRITE_BASE}/events/search/",
                        headers=headers,
                        params={
                            "q": term,
                            "location.address": f"{city}, India",
                            "location.within": "50km",
                            "start_date.range_start": "2026-01-01T00:00:00",
                            "expand": "venue,organizer",
                            "page_size": 20,
                        },
                        timeout=15,
                    )
                    if resp.status_code == 401:
                        print("  [Eventbrite] Invalid token")
                        return events
                    if resp.status_code != 200:
                        continue
                    for item in resp.json().get("events", []):
                        ev = self._parse(item)
                        if ev:
                            events.append(ev)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  [Eventbrite] {city}/{term}: {e}")

        return events

    def _parse(self, item: dict) -> Optional[RawEvent]:
        name = item.get("name", {}).get("text", "")
        if not name or len(name) < 4:
            return None
        url = item.get("url", "")
        venue = item.get("venue", {}) or {}
        addr = venue.get("address", {}) or {}
        return RawEvent(
            uid=hashlib.md5(url.encode()).hexdigest(),
            name=name,
            date_raw=item.get("start", {}).get("local", ""),
            date_start=parse_date(item.get("start", {}).get("local", "")),
            location_city=addr.get("city", ""),
            location_state=addr.get("region", ""),
            is_virtual=item.get("online_event", False),
            organizer=(item.get("organizer", {}) or {}).get("name", ""),
            description=clean_text(item.get("description", {}).get("text", "")),
            url=url,
            source="eventbrite",
            source_domain="eventbrite.com",
        )
