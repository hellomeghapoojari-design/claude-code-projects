"""DuckDuckGo search source — adapted from agent.py for Indian corporate speaker."""
import hashlib
import time
from app.discovery.sources.base import BaseSource, RawEvent

SEARCH_QUERIES = [
    "leadership summit India 2026 call for speakers",
    "corporate team building conference India 2026",
    "HR conference India 2026 keynote speaker",
    "motivation workshop India 2026 speaker",
    "organizational culture summit India 2026",
    "team building conference Bangalore 2026 speaker",
    "leadership development summit Mumbai 2026",
    "employee engagement conference Delhi 2026",
    "L&D conference India 2026 keynote",
    "corporate offsite speaker India 2026",
    "management conclave India 2026",
    "people and culture conference India 2026",
    "site:10times.com leadership India 2026",
    "site:townscript.com corporate team building India",
    "site:lu.ma leadership corporate India",
]

RESULTS_PER_QUERY = 8
SEARCH_PAUSE_SEC = 3.0

BLOCK_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "youtube.com",
    "reddit.com", "quora.com", "wikipedia.org", "medium.com",
    "forbes.com", "inc.com", "entrepreneur.com", "instagram.com",
}

BLOCK_PATH_PATTERNS = ["/stories/", "/blog/", "/news/", "/article", "/post/"]


class DDGSSearchSource(BaseSource):
    def fetch(self) -> list[RawEvent]:
        try:
            from ddgs import DDGS
        except ImportError:
            print("[WARN] ddgs not installed, skipping search source")
            return []

        from urllib.parse import urlparse

        seen: set[str] = set()
        urls: list[str] = []

        with DDGS() as ddgs:
            for query in SEARCH_QUERIES:
                print(f"  [DDGS] {query}")
                try:
                    results = list(ddgs.text(query, max_results=RESULTS_PER_QUERY))
                    for r in results:
                        u = r.get("href", "")
                        if not u:
                            continue
                        dom = urlparse(u).netloc.lower().replace("www.", "")
                        if dom in BLOCK_DOMAINS:
                            continue
                        path = urlparse(u).path.lower()
                        if any(p in path for p in BLOCK_PATH_PATTERNS):
                            continue
                        uid = hashlib.md5(u.encode()).hexdigest()
                        if uid not in seen:
                            seen.add(uid)
                            urls.append(u)
                except Exception as e:
                    print(f"  [WARN] DDGS query failed: {e}")
                time.sleep(SEARCH_PAUSE_SEC)

        # Return stub RawEvents; generic_scraper will fill them in via orchestrator
        events = []
        for url in urls:
            from urllib.parse import urlparse
            dom = urlparse(url).netloc.lower().replace("www.", "")
            ev = RawEvent(
                uid=hashlib.md5(url.encode()).hexdigest(),
                url=url,
                source="ddgs",
                source_domain=dom,
            )
            events.append(ev)
        return events
