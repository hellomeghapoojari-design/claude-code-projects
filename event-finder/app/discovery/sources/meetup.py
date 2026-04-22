"""Meetup GraphQL API source."""
import hashlib
import time
from typing import Optional, List
import requests
from app.discovery.sources.base import BaseSource, RawEvent
from app.discovery.sources.generic_scraper import parse_date, clean_text

INDIA_LOCATIONS = [
    ("Mumbai", 19.076, 72.877),
    ("Delhi", 28.613, 77.209),
    ("Bangalore", 12.972, 77.594),
    ("Hyderabad", 17.385, 78.487),
    ("Chennai", 13.083, 80.270),
    ("Pune", 18.520, 73.856),
]

MEETUP_GQL = "https://api.meetup.com/gql"
QUERY = """
query searchEvents($query: String!, $lat: Float!, $lon: Float!, $radius: Float!) {
  searchEvents(input: { query: $query, lat: $lat, lon: $lon, radius: $radius }, filter: { status: UPCOMING }) {
    edges {
      node {
        id
        title
        eventUrl
        dateTime
        description
        isOnline
        venue { city state }
        group { name }
        going
      }
    }
  }
}
"""


class MeetupSource(BaseSource):
    def __init__(self, token: str = ""):
        self.token = token

    def fetch(self) -> list[RawEvent]:
        events: list[RawEvent] = []
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        search_terms = [
            "leadership team building corporate",
            "motivation mindset professional",
            "HR learning development",
        ]

        for city, lat, lon in INDIA_LOCATIONS[:4]:
            for term in search_terms[:2]:
                try:
                    resp = requests.post(
                        MEETUP_GQL,
                        json={"query": QUERY, "variables": {"query": term, "lat": lat, "lon": lon, "radius": 80.0}},
                        headers=headers,
                        timeout=15,
                    )
                    if resp.status_code != 200:
                        continue
                    edges = (
                        resp.json()
                        .get("data", {})
                        .get("searchEvents", {})
                        .get("edges", [])
                    )
                    for edge in edges:
                        ev = self._parse(edge.get("node", {}))
                        if ev:
                            events.append(ev)
                    time.sleep(1)
                except Exception as e:
                    print(f"  [Meetup] {city}: {e}")

        return events

    def _parse(self, node: dict) -> Optional[RawEvent]:
        name = node.get("title", "")
        if not name or len(name) < 4:
            return None
        url = node.get("eventUrl", "")
        venue = node.get("venue", {}) or {}
        group = node.get("group", {}) or {}
        going = node.get("going")
        return RawEvent(
            uid=hashlib.md5(url.encode()).hexdigest(),
            name=name,
            date_raw=node.get("dateTime", ""),
            date_start=parse_date(node.get("dateTime", "")),
            location_city=venue.get("city", ""),
            is_virtual=node.get("isOnline", False),
            organizer=group.get("name", ""),
            description=clean_text(node.get("description", "")),
            audience_size=going,
            url=url,
            source="meetup",
            source_domain="meetup.com",
        )
