import hashlib
from difflib import SequenceMatcher
from app.discovery.sources.base import RawEvent


def make_uid(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def deduplicate(events: list[RawEvent]) -> list[RawEvent]:
    seen_uid: set[str] = set()
    result: list[RawEvent] = []

    for ev in events:
        if not ev.uid:
            ev.uid = make_uid(ev.url or ev.name)

        if ev.uid in seen_uid:
            continue

        # Fuzzy dedup: same name + same start date + same city from different sources
        is_dup = False
        for existing in result:
            if (
                ev.date_start
                and existing.date_start == ev.date_start
                and ev.location_city
                and existing.location_city.lower() == ev.location_city.lower()
                and _similar(ev.name, existing.name) > 0.85
            ):
                is_dup = True
                break

        if not is_dup:
            seen_uid.add(ev.uid)
            result.append(ev)

    return result
