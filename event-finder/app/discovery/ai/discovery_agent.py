"""AI-powered event discovery using Claude + DDGS search results."""
import hashlib
import json
import time
from app.discovery.sources.base import RawEvent
from app.discovery.sources.generic_scraper import parse_date, clean_text

AI_SEARCH_QUERIES = [
    "leadership summit India 2026 call for speakers site:lu.ma OR site:eventbrite.com",
    "corporate team building conference India 2026 keynote speaker",
    "HR conference learning development India 2026",
    "motivation workshop corporate India 2026 speaker",
    "management conclave India 2026 delegate",
    "people culture conference India 2026",
    "organizational leadership summit Bangalore Mumbai Delhi 2026",
    "corporate offsite facilitator speaker India 2026",
    "employee engagement summit India 2026",
    "startup leadership entrepreneurship India conference 2026",
]

DISCOVERY_PROMPT = """You are helping an Indian corporate/motivational speaker discover events to speak at.
The speaker's topics are: leadership, team building, motivation, organizational culture, employee engagement, high-performance teams.

Below are web search result snippets. Identify events that are relevant for this speaker.

For each relevant event, extract the following as JSON:
{
  "name": "Event name",
  "date_raw": "Date string as found",
  "location_city": "City in India or 'Virtual'",
  "event_type": "One of: leadership_summit | team_building | motivation_workshop | hr_conference | corporate_offsite | webinar | other_corporate",
  "url": "Event URL",
  "has_speaking": true/false,
  "description": "1-2 sentence summary",
  "organizer": "Organizer name if mentioned"
}

Return ONLY a JSON array. If no events are relevant, return [].

Search results:
{snippets}
"""


class AIDiscoveryAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self) -> list[RawEvent]:
        if not self.api_key:
            print("  [AI Discovery] No Anthropic API key, skipping")
            return []

        try:
            import anthropic
            from ddgs import DDGS
        except ImportError as e:
            print(f"  [AI Discovery] Missing dependency: {e}")
            return []

        client = anthropic.Anthropic(api_key=self.api_key)
        snippets: list[str] = []

        with DDGS() as ddgs:
            for query in AI_SEARCH_QUERIES[:6]:
                try:
                    results = list(ddgs.text(query, max_results=5))
                    for r in results:
                        snippet = f"URL: {r.get('href', '')}\nTitle: {r.get('title', '')}\nSnippet: {r.get('body', '')}"
                        snippets.append(snippet)
                    time.sleep(2)
                except Exception as e:
                    print(f"  [AI Discovery DDGS] {e}")

        if not snippets:
            return []

        combined = "\n\n---\n\n".join(snippets[:30])
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": DISCOVERY_PROMPT.format(snippets=combined),
                }],
            )
            raw_text = response.content[0].text.strip()
            # Extract JSON array from response
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            items = json.loads(raw_text[start:end])
        except Exception as e:
            print(f"  [AI Discovery Claude] {e}")
            return []

        events: list[RawEvent] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            url = item.get("url", "")
            if not name or len(name) < 4:
                continue
            ev = RawEvent(
                uid=hashlib.md5((url or name).encode()).hexdigest(),
                name=clean_text(name),
                date_raw=item.get("date_raw", ""),
                date_start=parse_date(item.get("date_raw", "")),
                location_city=item.get("location_city", ""),
                event_type=item.get("event_type", ""),
                description=clean_text(item.get("description", "")),
                url=url,
                organizer=item.get("organizer", ""),
                has_speaking=bool(item.get("has_speaking")),
                source="ai_discovery",
                source_domain="",
            )
            events.append(ev)

        print(f"  [AI Discovery] Found {len(events)} events from Claude")
        return events
