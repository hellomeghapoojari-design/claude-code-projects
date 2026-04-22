"""Generic HTML scraper — ported and adapted from agent.py."""
import re
import time
import random
import hashlib
import datetime
from urllib.parse import urlparse, urljoin
from typing import Optional
import requests
from bs4 import BeautifulSoup
from app.discovery.sources.base import RawEvent

REQUEST_TIMEOUT = 12
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0

USER_AGENTS = [
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

INDIA_VIRTUAL_KEYWORDS = ["online", "virtual", "remote", "livestream", "webinar"]
INDIA_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Noida", "Gurgaon", "Gurugram",
    "Chandigarh", "Kochi", "Indore", "Lucknow", "Surat",
]

STATIC_SEED_URLS = [
    "https://nasscom.in/events",
    "https://www.10times.com/india/leadership-events",
    "https://www.10times.com/india/business-events",
    "https://www.townscript.com/events/india/corporate",
]


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    })
    return s


def safe_get(session: requests.Session, url: str, retries: int = 2) -> Optional[BeautifulSoup]:
    for attempt in range(retries + 1):
        try:
            time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
            resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if resp.status_code == 429:
                wait = 30 + attempt * 20
                time.sleep(wait)
                continue
            if resp.status_code in (403, 404):
                return None
            if resp.status_code == 200:
                try:
                    return BeautifulSoup(resp.text, "lxml")
                except Exception:
                    return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            if attempt == retries:
                print(f"  [WARN] {url[:60]}: {e}")
    return None


def extract_jsonld(soup: BeautifulSoup) -> dict:
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string or ""
            data = json.loads(raw)
            if isinstance(data, list):
                data = next((d for d in data if isinstance(d, dict)), {})
            if isinstance(data, dict) and data.get("@type", "") in (
                "Event", "BusinessEvent", "SocialEvent", "EducationEvent"
            ):
                return data
        except Exception:
            continue
    return {}


def parse_date(raw: str) -> Optional[datetime.date]:
    if not raw:
        return None
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', raw)
    if m:
        try:
            return datetime.date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            pass
    m = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(202\d)', raw)
    if m:
        month = MONTH_MAP.get(m[1][:3].lower())
        if month:
            try:
                return datetime.date(int(m[3]), month, int(m[2]))
            except ValueError:
                pass
    m = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(202\d)', raw)
    if m:
        month = MONTH_MAP.get(m[2][:3].lower())
        if month:
            try:
                return datetime.date(int(m[3]), month, int(m[1]))
            except ValueError:
                pass
    return None


def clean_text(s: str, max_len: int = 300) -> str:
    return re.sub(r'\s+', ' ', s or "").strip()[:max_len]


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def _detect_city(text: str) -> str:
    tl = text.lower()
    for city in INDIA_CITIES:
        if city.lower() in tl:
            return city
    return ""


def scrape_page(url: str, session: requests.Session) -> Optional[RawEvent]:
    soup = safe_get(session, url)
    if not soup:
        return None

    dom = domain_of(url)
    ev = RawEvent(
        uid=hashlib.md5(url.encode()).hexdigest(),
        url=url,
        source="generic",
        source_domain=dom,
    )

    ld = extract_jsonld(soup)
    if ld:
        ev.name = ld.get("name", "")
        ev.date_raw = ld.get("startDate", "")
        loc = ld.get("location", {})
        if isinstance(loc, dict):
            addr = loc.get("address", {})
            ev.location_city = (
                loc.get("name", "")
                or (addr.get("addressLocality", "") if isinstance(addr, dict) else "")
            )
        org = ld.get("organizer", {})
        if isinstance(org, dict):
            ev.organizer = org.get("name", "")
        ev.description = clean_text(ld.get("description", ""))
        ev.event_type = ld.get("@type", "Event")

    if not ev.name:
        title = soup.find("title")
        raw_title = title.get_text() if title else ""
        ev.name = re.sub(r'\s*[|\-–:]\s*.{0,30}$', '', raw_title).strip()[:200]

    if not ev.date_raw:
        full_text = soup.get_text(" ", strip=True)
        m = re.search(
            r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
            r'Dec(?:ember)?)\s+\d{1,2},?\s+202[678]\b', full_text, re.I
        )
        if m:
            ev.date_raw = m.group(0)
        else:
            m2 = re.search(r'202[678]-\d{2}-\d{2}', full_text)
            if m2:
                ev.date_raw = m2.group(0)

    ev.date_start = parse_date(ev.date_raw)

    if not ev.location_city:
        full_text = soup.get_text(" ", strip=True)
        if any(kw in full_text.lower() for kw in INDIA_VIRTUAL_KEYWORDS):
            ev.is_virtual = True
        else:
            ev.location_city = _detect_city(full_text)

    if not ev.organizer:
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            ev.organizer = meta_author.get("content", "")

    if not ev.description:
        meta_desc = (
            soup.find("meta", attrs={"name": "description"})
            or soup.find("meta", attrs={"property": "og:description"})
        )
        if meta_desc:
            ev.description = clean_text(meta_desc.get("content", ""))

    if not ev.contact_url:
        mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
        if mailto:
            ev.contact_email = mailto["href"].replace("mailto:", "")
        contact_link = soup.find("a", href=re.compile(r"/contact|/cfp|/speak|/apply", re.I))
        if contact_link:
            ev.contact_url = urljoin(url, contact_link["href"])

    full_text_lower = soup.get_text(" ", strip=True).lower()
    from app.discovery.scorer import _detect_signals
    hs, hp = _detect_signals(full_text_lower)
    ev.has_speaking = hs
    ev.has_partnership = hp

    return ev if (ev.name and len(ev.name) >= 4) else None
