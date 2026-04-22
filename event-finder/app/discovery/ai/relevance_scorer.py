"""Batch relevance scoring of events using Claude Haiku."""
import json
from sqlalchemy.orm import Session
from app.models.event import Event

SCORE_PROMPT = """You are evaluating events for an Indian corporate/motivational speaker whose topics are:
- Leadership and high-performance teams
- Motivation and mindset for organisations
- Team building and culture transformation
- Employee engagement and wellbeing

Rate each event for relevance (1-10) and list 2-3 keyword tags.

Events (JSON array):
{events_json}

Return a JSON array with one object per event in the same order:
[{{"id": <id>, "relevance_score": <1-10>, "tags": ["tag1", "tag2"], "reason": "brief reason"}}]
Return ONLY valid JSON, nothing else."""


class RelevanceScorer:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def score_pending(self, db: Session, batch_size: int = 10) -> int:
        if not self.api_key:
            return 0

        try:
            import anthropic
        except ImportError:
            return 0

        # Get events without AI scoring (score == 0 and no relevance tags)
        events = (
            db.query(Event)
            .filter(Event.score == 0, Event.relevance_tags == None)  # noqa: E711
            .limit(batch_size)
            .all()
        )
        if not events:
            return 0

        client = anthropic.Anthropic(api_key=self.api_key)
        payload = [
            {
                "id": ev.id,
                "name": ev.name,
                "description": (ev.description or "")[:300],
                "event_type": ev.event_type or "",
            }
            for ev in events
        ]

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": SCORE_PROMPT.format(events_json=json.dumps(payload)),
                }],
            )
            raw = response.content[0].text.strip()
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == 0:
                return 0
            results = json.loads(raw[start:end])
        except Exception as e:
            print(f"  [RelevanceScorer] {e}")
            return 0

        updated = 0
        result_map = {r["id"]: r for r in results if isinstance(r, dict)}
        for ev in events:
            r = result_map.get(ev.id)
            if not r:
                continue
            ev.score = max(1, min(10, int(r.get("relevance_score", 5))))
            ev.relevance_tags = r.get("tags", [])
            updated += 1

        db.commit()
        return updated
