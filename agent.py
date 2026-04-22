import sys, os, re, json, time, random, hashlib, datetime, webbrowser
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from urllib.parse import urlparse, urljoin


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

def _require(pkg_import, pip_name):
    try:
        return __import__(pkg_import)
    except ImportError:
        print(f"[ERROR] Missing package. Run: pip3 install {pip_name}")
        sys.exit(1)

requests_mod  = _require("requests",      "requests")
_require("bs4",  "beautifulsoup4")
_require("ddgs", "ddgs")

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEARCH_QUERIES = [
    "startup conference 2026 call for speakers",
    "entrepreneurship summit 2026 speaking opportunity",
    "VC founder event 2026 call for proposals",
    "startup ecosystem event 2026 site:lu.ma OR site:eventbrite.com",
    "accelerator demo day 2026 partners sponsors",
    "enterprise SaaS conference 2026 speaking",
    "B2B startup summit 2026 sponsor opportunities",
]

SEED_URLS = [
    "https://sessionize.com/events",
    "https://papercall.io/cfps",
    "https://lu.ma/startup",
    "https://www.eventbrite.com/d/online/startup-conference/",
]

RESULTS_PER_QUERY = 8
SEARCH_PAUSE_SEC  = 3.5
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0
REQUEST_TIMEOUT   = 12
MAX_SCRAPE_URLS   = 55

# Domains/path patterns to skip — irrelevant to event discovery
BLOCK_DOMAINS = {
    "forums.att.com", "att.com", "weforum.org", "linkedin.com",
    "facebook.com", "twitter.com", "x.com", "youtube.com",
    "reddit.com", "quora.com", "wikipedia.org", "medium.com",
    "forbes.com", "inc.com", "entrepreneur.com",
}
BLOCK_PATH_PATTERNS = ["/stories/", "/blog/", "/news/", "/article", "/post/"]

# URL signals that strongly imply a speaking or partnership opportunity
URL_SPEAKING_SIGNALS    = ["call-for-speakers", "cfp", "speak-at", "speaking",
                           "call-for-proposals", "submit-a-talk", "apply-to-speak"]
URL_PARTNERSHIP_SIGNALS = ["sponsor", "partnership", "exhibitor", "partner"]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")

ICP_SIGNALS = [
    "enterprise", "vp ", "director", "c-suite", "cto", "cmo", "cso", "ceo",
    "decision maker", "b2b", "saas", "fortune 500", "mid-market",
    "corporate innovation", "digital transformation", "procurement",
    "executive", "leadership",
]

SPEAKING_SIGNALS = [
    "call for speakers", "cfp", "call for proposals", "speaking opportunity",
    "submit a talk", "apply to speak", "speaker application", "speak at",
    "call for presentations",
]

PARTNERSHIP_SIGNALS = [
    "sponsor", "partnership", "exhibitor", "partner opportunity",
    "lead generation", "booth", "demo day", "become a partner",
]

USER_AGENTS = [
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
]

MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Event:
    uid: str = ""
    name: str = ""
    event_type: str = ""
    date_raw: str = ""
    date_parsed: Optional[datetime.date] = None
    location: str = ""
    organizer: str = ""
    audience: str = ""
    url: str = ""
    contact: str = ""
    score: int = 0
    score_breakdown: dict = field(default_factory=dict)
    has_speaking: bool = False
    has_partnership: bool = False
    icp_fit: int = 0
    authority: int = 0
    lead_potential: int = 0
    deadline_proximity: int = 0
    outreach_message: str = ""
    speaking_title: str = ""
    speaking_topic: str = ""
    source_domain: str = ""
    scrape_error: str = ""


# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return s


def safe_get(session: requests.Session, url: str, retries: int = 2) -> Optional[BeautifulSoup]:
    for attempt in range(retries + 1):
        try:
            time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
            resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if resp.status_code == 429:
                wait = 30 + attempt * 20
                print(f"    [RATE LIMIT] sleeping {wait}s...")
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
                print(f"    [WARN] {url[:60]}: {e}")
    return None


def extract_jsonld(soup: BeautifulSoup) -> dict:
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


def detect_signals(text: str) -> tuple[bool, bool]:
    tl = text.lower()
    has_speaking    = any(s in tl for s in SPEAKING_SIGNALS)
    has_partnership = any(s in tl for s in PARTNERSHIP_SIGNALS)
    return has_speaking, has_partnership


def clean_text(s: str, max_len: int = 300) -> str:
    return re.sub(r'\s+', ' ', s or "").strip()[:max_len]


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


# ---------------------------------------------------------------------------
# Per-source scrapers
# ---------------------------------------------------------------------------

def scrape_luma(soup: BeautifulSoup, url: str) -> Event:
    ev = Event()
    try:
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            data = json.loads(script.string)
            ep = data.get("props", {}).get("pageProps", {}).get("event", {})
            ev.name = ep.get("name", "")
            ev.date_raw = ep.get("start_at", "")
            geo = ep.get("geo_address_info", {})
            ev.location = geo.get("city", "") or geo.get("description", "")
            hosts = ep.get("hosts", [])
            if hosts:
                ev.organizer = hosts[0].get("name", "") if isinstance(hosts[0], dict) else ""
            ev.audience = clean_text(ep.get("description", ""))
            ev.event_type = "Event"
    except Exception:
        pass
    if not ev.name:
        title = soup.find("title")
        ev.name = clean_text(title.get_text() if title else "", 120)
    return ev


def scrape_eventbrite(soup: BeautifulSoup, url: str) -> Event:
    ev = Event()
    ld = extract_jsonld(soup)
    if ld:
        ev.name      = ld.get("name", "")
        ev.date_raw  = ld.get("startDate", "")
        loc = ld.get("location", {})
        if isinstance(loc, dict):
            ev.location = loc.get("name", "") or loc.get("address", {}).get("addressLocality", "")
        org = ld.get("organizer", {})
        if isinstance(org, dict):
            ev.organizer = org.get("name", "")
        ev.audience = clean_text(ld.get("description", ""))
        ev.event_type = "Conference"
    if not ev.name:
        title = soup.find("title")
        ev.name = re.sub(r'\s*[|\-–]\s*Eventbrite.*$', '', title.get_text() if title else "").strip()
    return ev


def scrape_sessionize(soup: BeautifulSoup, url: str) -> Event:
    ev = Event()
    ev.has_speaking = True
    ev.event_type = "Conference (CFP)"
    try:
        h1 = soup.find("h1")
        ev.name = clean_text(h1.get_text() if h1 else "", 120)
        date_el = soup.find(string=re.compile(r'202[56]', re.I))
        if date_el:
            ev.date_raw = clean_text(str(date_el), 80)
        desc = soup.find("div", class_=re.compile(r"description|about|info", re.I))
        ev.audience = clean_text(desc.get_text() if desc else "", 300)
    except Exception:
        pass
    if not ev.name:
        title = soup.find("title")
        ev.name = clean_text(title.get_text() if title else "", 120)
    return ev


def scrape_papercall(soup: BeautifulSoup, url: str) -> Event:
    ev = Event()
    ev.has_speaking = True
    ev.event_type = "Conference (CFP)"
    try:
        h1 = soup.find("h1") or soup.find("h2")
        ev.name = clean_text(h1.get_text() if h1 else "", 120)
        deadline_el = soup.find(string=re.compile(r'deadline|closes|due', re.I))
        if deadline_el:
            ev.date_raw = clean_text(str(deadline_el), 80)
        desc = soup.find("div", class_=re.compile(r"description|detail|body", re.I))
        ev.audience = clean_text(desc.get_text() if desc else "", 300)
    except Exception:
        pass
    return ev


def scrape_generic(soup: BeautifulSoup, url: str) -> Event:
    ev = Event()
    ld = extract_jsonld(soup)
    if ld:
        ev.name     = ld.get("name", "")
        ev.date_raw = ld.get("startDate", "")
        loc = ld.get("location", {})
        if isinstance(loc, dict):
            ev.location = (loc.get("name", "") or
                           loc.get("address", {}).get("addressLocality", "") if isinstance(loc.get("address"), dict) else "")
        org = ld.get("organizer", {})
        if isinstance(org, dict):
            ev.organizer = org.get("name", "")
        ev.audience  = clean_text(ld.get("description", ""))
        ev.event_type = ld.get("@type", "Event")

    if not ev.name:
        title = soup.find("title")
        raw_title = title.get_text() if title else ""
        ev.name = re.sub(r'\s*[|\-–:]\s*.{0,30}$', '', raw_title).strip()[:120]

    if not ev.date_raw:
        full_text = soup.get_text(" ", strip=True)
        m = re.search(r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
                      r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
                      r'Dec(?:ember)?)\s+\d{1,2},?\s+202[56]\b', full_text, re.I)
        if m:
            ev.date_raw = m.group(0)
        else:
            m2 = re.search(r'202[56]-\d{2}-\d{2}', full_text)
            if m2:
                ev.date_raw = m2.group(0)

    if not ev.location:
        full_text = soup.get_text(" ", strip=True)
        if re.search(r'\b(online|virtual|remote|livestream)\b', full_text, re.I):
            ev.location = "Virtual"

    if not ev.organizer:
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            ev.organizer = meta_author.get("content", "")

    if not ev.audience:
        meta_desc = soup.find("meta", attrs={"name": "description"}) or \
                    soup.find("meta", attrs={"property": "og:description"})
        if meta_desc:
            ev.audience = clean_text(meta_desc.get("content", ""))

    if not ev.contact:
        mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
        if mailto:
            ev.contact = mailto["href"]
        else:
            contact_link = soup.find("a", href=re.compile(r"/contact|/cfp|/speak|/apply", re.I))
            if contact_link:
                ev.contact = urljoin(url, contact_link["href"])

    return ev


SCRAPER_MAP = {
    "lu.ma":          scrape_luma,
    "luma.com":       scrape_luma,
    "eventbrite.com": scrape_eventbrite,
    "sessionize.com": scrape_sessionize,
    "papercall.io":   scrape_papercall,
}


def scrape_url(url: str, session: requests.Session) -> Optional[Event]:
    dom = domain_of(url)
    scraper = SCRAPER_MAP.get(dom, scrape_generic)
    soup = safe_get(session, url)
    if not soup:
        return None
    try:
        ev = scraper(soup, url)
        ev.uid          = hashlib.md5(url.encode()).hexdigest()
        ev.url          = url
        ev.source_domain = dom

        full_text = soup.get_text(" ", strip=True).lower()
        hs, hp = detect_signals(full_text)
        ev.has_speaking    = ev.has_speaking or hs
        ev.has_partnership = ev.has_partnership or hp

        if not ev.date_parsed and ev.date_raw:
            ev.date_parsed = parse_date(ev.date_raw)

        # Pull sub-event links from listing pages (sessionize, papercall)
        if dom in ("sessionize.com", "papercall.io") and not ev.name:
            links = []
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                if dom in href and href != url:
                    links.append(href)
            ev.scrape_error = "listing:" + "|".join(links[:10])

        return ev
    except Exception as e:
        uid = hashlib.md5(url.encode()).hexdigest()
        return Event(uid=uid, url=url, source_domain=dom, scrape_error=str(e))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def run_searches() -> List[str]:
    seen = set()
    urls = []

    with DDGS() as ddgs:
        for query in SEARCH_QUERIES:
            print(f"  [SEARCH] {query}")
            try:
                results = list(ddgs.text(query, max_results=RESULTS_PER_QUERY))
                added = 0
                for r in results:
                    u = r.get("href", "")
                    if not u:
                        continue
                    uid = hashlib.md5(u.encode()).hexdigest()
                    if uid not in seen:
                        seen.add(uid)
                        urls.append(u)
                        added += 1
                print(f"           +{added} new URLs (total: {len(urls)})")
            except Exception as e:
                print(f"           [WARN] search failed: {e}")
            time.sleep(SEARCH_PAUSE_SEC)

    return urls


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_event(ev: Event) -> Event:
    today = datetime.date.today()
    text  = f"{ev.name} {ev.audience} {ev.organizer} {ev.event_type}".lower()

    # Boost has_speaking / has_partnership from URL signals if not already set
    url_lower = ev.url.lower()
    if not ev.has_speaking and any(s in url_lower for s in URL_SPEAKING_SIGNALS):
        ev.has_speaking = True
    if not ev.has_partnership and any(s in url_lower for s in URL_PARTNERSHIP_SIGNALS):
        ev.has_partnership = True

    # ICP Fit
    # Also search URL for ICP signals
    url_text = ev.url.lower().replace("-", " ").replace("/", " ")
    full_text = text + " " + url_text

    hits = sum(1 for s in ICP_SIGNALS if s in full_text)
    icp_table = [1, 1, 4, 4, 7, 7, 10, 10, 10, 10, 10]
    icp = float(icp_table[min(hits, 10)])
    for bonus_word in ["vp", "director", "c-suite", "cxo", "enterprise", "b2b", "saas"]:
        if bonus_word in full_text:
            icp = min(10.0, icp + 2)
            break

    # Authority — domain map + URL/name keyword signals
    AUTHORITY_DOMAINS = {
        "sessionize.com": 9, "papercall.io": 9,
        "lu.ma": 8, "luma.com": 8,
        "techcrunch.com": 8, "vcconf.com": 8,
        "eventbrite.com": 6, "bigevent.io": 6,
        "forrester.com": 9, "gartner.com": 9,
        "saas.group": 7, "founderpath.com": 7,
        "startupevents.org": 7, "vcfastpitch.com": 7,
        "kindcongress.com": 6, "scitechseries.com": 6,
        "b2bconnect.wbresearch.com": 7,
    }
    authority = float(AUTHORITY_DOMAINS.get(ev.source_domain, 4))

    # Boost authority from known brand signals in text or URL
    HIGH_AUTH_SIGNALS = ["techcrunch", "ycombinator", "y combinator", "a16z",
                         "sequoia", "forrester", "gartner", "wharton", "harvard",
                         "stanford", "mit ", "sxsw", "web summit", "collision"]
    for sig in HIGH_AUTH_SIGNALS:
        if sig in full_text:
            authority = min(10.0, authority + 2)
            break

    for w in ["annual", "global", "international", "world", "summit", "forum"]:
        if w in ev.name.lower() or w in url_text:
            authority = min(10.0, authority + 1)
            break

    # Lead Potential — base score for any event-looking page
    EVENT_URL_SIGNALS = ["conference", "summit", "event", "forum", "expo",
                         "meetup", "founder", "startup", "accelerator"]
    is_event_page = any(s in url_text for s in EVENT_URL_SIGNALS)
    lead = 2.0 if is_event_page else 0.0  # base for event pages

    if ev.has_speaking:    lead += 5
    if ev.has_partnership: lead += 3
    m = re.search(r'(\d[\d,]+)\s*(attendees|participants|professionals|delegates)', full_text)
    if m:
        n = int(m.group(1).replace(",", ""))
        lead += 3 if n >= 1000 else (2 if n >= 500 else 1)
    lead = min(10.0, lead)

    # Deadline Proximity
    if ev.date_parsed:
        delta = (ev.date_parsed - today).days
        if delta < 0:
            ev.score = 0
            return ev
        if delta <= 30:    deadline = 10.0
        elif delta <= 60:  deadline = 8.0
        elif delta <= 90:  deadline = 6.0
        elif delta <= 180: deadline = 4.0
        else:              deadline = 2.0
    else:
        deadline = 3.0

    ev.icp_fit            = round(icp)
    ev.authority          = round(authority)
    ev.lead_potential     = round(lead)
    ev.deadline_proximity = round(deadline)
    ev.score_breakdown    = {"icp": round(icp, 1), "authority": round(authority, 1),
                             "lead": round(lead, 1), "deadline": round(deadline, 1)}
    raw = icp * 0.35 + authority * 0.25 + lead * 0.25 + deadline * 0.15
    ev.score = max(1, min(10, round(raw)))
    return ev


# ---------------------------------------------------------------------------
# Outreach + speaking topic generation
# ---------------------------------------------------------------------------

TOPIC_TEMPLATES = [
    (
        lambda ev: "saas" in ev.audience.lower() or "b2b" in ev.audience.lower(),
        "From Seed to Enterprise: How B2B Startups Win Fortune 500 Accounts",
        "A tactical framework for founders to land enterprise customers — covering procurement cycles, "
        "stakeholder mapping, and closing multi-year contracts.",
    ),
    (
        lambda ev: "digital transformation" in ev.audience.lower() or "corporate" in ev.audience.lower(),
        "Building for the Enterprise Buyer: What VPs Actually Want from Startups",
        "Practical guide for startup founders navigating enterprise sales — how to speak the language "
        "of VPs and Directors, run pilots that convert, and structure deals that scale.",
    ),
    (
        lambda ev: ev.has_partnership or "sponsor" in ev.audience.lower(),
        "Partnership-Led Growth: How Startups Build Pipeline Without a Sales Team",
        "Case studies of startup partnerships that generated enterprise leads — from co-marketing "
        "to channel deals — with a playbook attendees can implement immediately.",
    ),
    (
        lambda ev: "accelerator" in ev.name.lower() or "demo day" in ev.name.lower(),
        "The Founder's Guide to Enterprise: Skipping the SMB Trap",
        "Why early-stage founders should target enterprise from day one — unit economics, feedback "
        "quality, and how to de-risk a long sales cycle.",
    ),
    (
        lambda _: True,
        "Selling to the Enterprise: A Founder's Unconventional Playbook",
        "Hard-won lessons from building B2B enterprise relationships — how startup founders can reach "
        "VP-level buyers, shorten sales cycles, and turn pilots into long-term contracts.",
    ),
]

OUTREACH_SPEAKING = """\
Subject: Speaking Proposal — {event_name}

Hi {organizer_name},

I came across {event_name} and was excited to see you're accepting speaker submissions — this looks like exactly the right room.

I work with early-stage B2B founders who are trying to crack enterprise accounts, and I've developed a framework specifically around what VP and Director-level buyers actually respond to. My proposed talk:

Title: "{speaking_title}"

Core takeaway: {speaking_topic}

Your audience of {audience_hint} would walk away with an immediately actionable playbook — not theory.

Happy to share an abstract, past talk recordings, or a brief call. What's the best next step?

Best,
[Your Name]
[Your Title] | [Company]
[LinkedIn / Website]\
"""

OUTREACH_PARTNERSHIP = """\
Subject: Partnership Opportunity — {event_name}

Hi {organizer_name},

I noticed {event_name} is bringing together {audience_hint} — a conversation I'd love to be part of as a partner.

We work at the intersection of [your value prop], and our ideal customer is exactly the enterprise decision-maker your event attracts. A partnership could take the form of a sponsored session, co-branded content, or a curated roundtable.

I'd love to explore what would add genuine value for your attendees — not just a logo on a slide.

Would a 20-minute call this week or next work for you?

Best,
[Your Name]
[Your Title] | [Company]
[LinkedIn / Website]\
"""

OUTREACH_GENERIC = """\
Subject: Connecting Around {event_name}

Hi {organizer_name},

I came across {event_name} and was impressed by the focus on {audience_hint}. This is a space where I do a lot of work.

I'd love to explore whether there's an opportunity to contribute — whether as a speaker, partner, or sponsor. I have a specific angle around enterprise sales that tends to resonate with founders and investors.

Would love to connect — even a brief intro call would be a great starting point.

Best,
[Your Name]
[Your Title] | [Company]
[LinkedIn / Website]\
"""


def generate_speaking_topic(ev: Event) -> tuple[str, str]:
    for condition, title, description in TOPIC_TEMPLATES:
        try:
            if condition(ev):
                return title, description
        except Exception:
            continue
    return TOPIC_TEMPLATES[-1][1], TOPIC_TEMPLATES[-1][2]


def generate_outreach(ev: Event) -> str:
    if ev.has_speaking:
        template = OUTREACH_SPEAKING
    elif ev.has_partnership:
        template = OUTREACH_PARTNERSHIP
    else:
        template = OUTREACH_GENERIC

    organizer_name = (ev.organizer.split()[0] if ev.organizer else "there")
    audience_hint  = (ev.audience[:80].strip() if ev.audience else "founders and enterprise leaders")
    topic_short    = ev.speaking_topic[:100] + "..." if len(ev.speaking_topic) > 100 else ev.speaking_topic

    return template.format(
        event_name      = ev.name or "your event",
        organizer_name  = organizer_name,
        speaking_title  = ev.speaking_title,
        speaking_topic  = topic_short,
        audience_hint   = audience_hint,
    )


# ---------------------------------------------------------------------------
# Dashboard HTML renderer
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Event Discovery Dashboard</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ min-height: 100vh; background: #0f0f1a; font-family: 'Segoe UI', sans-serif;
            color: #e0e0e0; padding: 24px 20px 60px; }}

    /* Header */
    .dashboard-header {{ text-align: center; padding: 40px 0 28px; }}
    .dashboard-header h1 {{
      font-size: 2.2rem; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 8px;
      background: linear-gradient(135deg, #a78bfa, #60a5fa);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .subtitle {{ color: #94a3b8; font-size: 0.95rem; margin-bottom: 6px; }}
    .run-meta {{ color: #64748b; font-size: 0.78rem; }}

    /* Stats */
    .stats-bar {{ display: flex; gap: 36px; justify-content: center; margin: 28px 0; flex-wrap: wrap; }}
    .stat-box {{ text-align: center; }}
    .stat-value {{ font-size: 2rem; font-weight: 700; }}
    .stat-label {{ font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase; color: #64748b; }}
    .stat-total   {{ color: #a78bfa; }}
    .stat-high    {{ color: #f472b6; }}
    .stat-medium  {{ color: #34d399; }}
    .stat-speaking {{ color: #60a5fa; }}

    /* Filter bar */
    .filter-bar {{ display: flex; gap: 10px; justify-content: center; margin-bottom: 32px; flex-wrap: wrap; align-items: center; }}
    .filter-btn {{
      padding: 8px 20px; border-radius: 8px; border: 1px solid #2d2d44;
      background: #1e1e2e; color: #94a3b8; cursor: pointer;
      font-size: 0.82rem; font-weight: 600; letter-spacing: 1px; transition: all 0.2s;
    }}
    .filter-btn.active, .filter-btn:hover {{
      background: linear-gradient(135deg, #a78bfa, #60a5fa);
      color: #0f0f1a; border-color: transparent;
    }}
    .sort-select {{
      padding: 8px 14px; border-radius: 8px; background: #1e1e2e;
      border: 1px solid #2d2d44; color: #94a3b8; font-size: 0.82rem; cursor: pointer;
    }}

    /* Section headers */
    .section-header {{ display: flex; align-items: center; gap: 12px; margin: 32px 0 18px; }}
    .section-header h2 {{ font-size: 1.1rem; letter-spacing: 2px; text-transform: uppercase; }}
    .section-header.high h2   {{ color: #f472b6; }}
    .section-header.medium h2 {{ color: #34d399; }}
    .section-count {{
      background: #2d2d44; border-radius: 20px;
      padding: 2px 10px; font-size: 0.72rem; color: #94a3b8;
    }}

    /* Grid */
    .events-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 18px; margin-bottom: 12px;
    }}

    /* Card */
    .event-card {{
      background: #1e1e2e; border: 2px solid #2d2d44; border-radius: 12px;
      padding: 22px; transition: border-color 0.2s, transform 0.15s;
      border-left-width: 4px;
    }}
    .event-card:hover {{ border-color: #a78bfa; transform: translateY(-2px); }}
    .event-card.high   {{ border-left-color: #f472b6; }}
    .event-card.medium {{ border-left-color: #34d399; }}

    /* Card header */
    .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 14px; }}
    .event-name  {{ font-size: 1rem; font-weight: 700; flex: 1; line-height: 1.4; }}
    .priority-badge {{ padding: 3px 10px; border-radius: 20px; font-size: 0.68rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; white-space: nowrap; }}
    .badge-high   {{ background: #2d1f4a; color: #f472b6; border: 1px solid #f472b633; }}
    .badge-medium {{ background: #0f2d20; color: #34d399; border: 1px solid #34d39933; }}

    /* Score */
    .score-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
    .score-number {{
      font-size: 1.9rem; font-weight: 900;
      background: linear-gradient(135deg, #a78bfa, #60a5fa);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; min-width: 36px;
    }}
    .score-bar-wrap {{ flex: 1; height: 5px; background: #2d2d44; border-radius: 3px; }}
    .score-bar {{ height: 100%; border-radius: 3px; background: linear-gradient(90deg, #a78bfa, #60a5fa); }}
    .score-denom {{ font-size: 0.68rem; color: #64748b; }}

    /* Meta */
    .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }}
    .meta-label {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 2px; }}
    .meta-value {{ font-size: 0.84rem; color: #94a3b8; }}
    .meta-full  {{ margin-bottom: 12px; }}

    /* Tags */
    .tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }}
    .tag {{ padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; }}
    .tag-speaking    {{ background: #1e2d4a; color: #60a5fa; }}
    .tag-partnership {{ background: #2d1e2d; color: #a78bfa; }}

    /* Links */
    .card-links {{ display: flex; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }}
    .card-link {{ color: #60a5fa; font-size: 0.8rem; text-decoration: none; border-bottom: 1px solid #60a5fa44; transition: border-color 0.2s; }}
    .card-link:hover {{ border-color: #60a5fa; }}

    /* Outreach */
    .outreach-section {{ background: #0f0f1a; border-radius: 8px; padding: 14px; margin-top: 14px; }}
    .outreach-header  {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
    .outreach-label   {{ font-size: 0.68rem; letter-spacing: 1.5px; text-transform: uppercase; color: #64748b; }}
    .copy-btn {{
      padding: 5px 12px; border-radius: 6px; border: 1px solid #2d2d44;
      background: transparent; color: #94a3b8; font-size: 0.72rem; cursor: pointer; transition: all 0.2s;
    }}
    .copy-btn:hover  {{ background: #a78bfa; color: #0f0f1a; border-color: #a78bfa; }}
    .copy-btn.copied {{ background: #34d399; color: #0f0f1a; border-color: #34d399; }}
    .outreach-text {{ font-size: 0.78rem; color: #94a3b8; white-space: pre-wrap; line-height: 1.65; max-height: 180px; overflow-y: auto; font-family: inherit; }}

    /* Speaking topic */
    .speaking-topic {{ background: #2d1f4a; border-radius: 8px; padding: 12px 14px; margin-top: 10px; }}
    .topic-label {{ font-size: 0.65rem; color: #a78bfa; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px; }}
    .topic-title {{ font-size: 0.88rem; font-weight: 700; color: #e0e0e0; line-height: 1.4; }}

    /* Empty */
    .empty-state {{ text-align: center; padding: 60px; color: #64748b; font-size: 1rem; }}

    @media (max-width: 600px) {{
      .events-grid  {{ grid-template-columns: 1fr; }}
      .meta-grid    {{ grid-template-columns: 1fr; }}
      .stats-bar    {{ gap: 20px; }}
    }}
  </style>
</head>
<body>

<div class="dashboard-header">
  <h1>Event Discovery</h1>
  <div class="subtitle">Startup &amp; Entrepreneurship &mdash; Speaking &amp; Partnership Opportunities</div>
  <div class="run-meta">Generated {generated_at} &mdash; targeting enterprise decision-makers</div>
</div>

<div class="stats-bar">
  <div class="stat-box"><div class="stat-value stat-total"  id="stat-total">0</div><div class="stat-label">Total</div></div>
  <div class="stat-box"><div class="stat-value stat-high"   id="stat-high">0</div><div class="stat-label">High Priority</div></div>
  <div class="stat-box"><div class="stat-value stat-medium" id="stat-medium">0</div><div class="stat-label">Medium Priority</div></div>
  <div class="stat-box"><div class="stat-value stat-speaking" id="stat-speaking">0</div><div class="stat-label">Speaking Opps</div></div>
</div>

<div class="filter-bar">
  <button class="filter-btn active" data-filter="all">All</button>
  <button class="filter-btn" data-filter="high">High Priority</button>
  <button class="filter-btn" data-filter="medium">Medium Priority</button>
  <button class="filter-btn" data-filter="speaking">Speaking</button>
  <button class="filter-btn" data-filter="partnership">Partnership</button>
  <select class="sort-select" id="sort-select">
    <option value="score">Sort: Score</option>
    <option value="date">Sort: Date</option>
    <option value="name">Sort: Name</option>
  </select>
</div>

<div id="events-container"></div>

<script>
const EVENTS = {events_json};

let currentFilter = 'all';
let currentSort   = 'score';

function esc(s) {{
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function computeStats() {{
  document.getElementById('stat-total').textContent    = EVENTS.length;
  document.getElementById('stat-high').textContent     = EVENTS.filter(e => e.score >= 8).length;
  document.getElementById('stat-medium').textContent   = EVENTS.filter(e => e.score >= 5 && e.score < 8).length;
  document.getElementById('stat-speaking').textContent = EVENTS.filter(e => e.has_speaking).length;
}}

function getFiltered() {{
  return EVENTS.filter(e => {{
    if (currentFilter === 'all')         return true;
    if (currentFilter === 'high')        return e.score >= 8;
    if (currentFilter === 'medium')      return e.score >= 5 && e.score < 8;
    if (currentFilter === 'speaking')    return e.has_speaking;
    if (currentFilter === 'partnership') return e.has_partnership;
  }});
}}

function getSorted(events) {{
  return [...events].sort((a, b) => {{
    if (currentSort === 'score') return b.score - a.score;
    if (currentSort === 'date')  return (a.date_raw || 'z').localeCompare(b.date_raw || 'z');
    if (currentSort === 'name')  return (a.name || '').localeCompare(b.name || '');
  }});
}}

function copyOutreach(uid) {{
  const ev = EVENTS.find(e => e.uid === uid);
  if (!ev) return;
  navigator.clipboard.writeText(ev.outreach_message).then(() => {{
    const btn = document.getElementById('copy-' + uid);
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {{ btn.textContent = 'Copy'; btn.classList.remove('copied'); }}, 2000);
  }});
}}

function cardHTML(ev) {{
  const isHigh = ev.score >= 8;
  const cls    = isHigh ? 'high' : 'medium';
  const barPct = (ev.score / 10 * 100) + '%';
  const tags   = [
    ev.has_speaking    ? '<span class="tag tag-speaking">Speaking</span>'    : '',
    ev.has_partnership ? '<span class="tag tag-partnership">Partnership</span>' : '',
  ].join('');
  const outreachBlock = isHigh ? `
    <div class="outreach-section">
      <div class="outreach-header">
        <span class="outreach-label">Outreach Template</span>
        <button class="copy-btn" id="copy-${{esc(ev.uid)}}" onclick="copyOutreach('${{esc(ev.uid)}}')">Copy</button>
      </div>
      <pre class="outreach-text">${{esc(ev.outreach_message)}}</pre>
    </div>
    <div class="speaking-topic">
      <div class="topic-label">Suggested Speaking Topic</div>
      <div class="topic-title">${{esc(ev.speaking_title)}}</div>
    </div>` : '';

  return `
  <div class="event-card ${{cls}}">
    <div class="card-header">
      <div class="event-name">${{esc(ev.name)}}</div>
      <span class="priority-badge badge-${{cls}}">${{isHigh ? 'High' : 'Medium'}}</span>
    </div>
    <div class="score-row">
      <div class="score-number">${{ev.score}}</div>
      <div class="score-bar-wrap"><div class="score-bar" style="width:${{barPct}}"></div></div>
      <div class="score-denom">/10</div>
    </div>
    <div class="meta-grid">
      <div><div class="meta-label">Type</div><div class="meta-value">${{esc(ev.event_type || '—')}}</div></div>
      <div><div class="meta-label">Date</div><div class="meta-value">${{esc(ev.date_raw || '—')}}</div></div>
      <div><div class="meta-label">Location</div><div class="meta-value">${{esc(ev.location || '—')}}</div></div>
      <div><div class="meta-label">Organizer</div><div class="meta-value">${{esc(ev.organizer || '—')}}</div></div>
    </div>
    ${{ev.audience ? `<div class="meta-full"><div class="meta-label">Audience</div><div class="meta-value">${{esc(ev.audience.slice(0,160))}}</div></div>` : ''}}
    <div class="tags">${{tags}}</div>
    <div class="card-links">
      <a class="card-link" href="${{esc(ev.url)}}" target="_blank" rel="noopener">Event Page ↗</a>
      ${{ev.contact && ev.contact !== ev.url ? `<a class="card-link" href="${{esc(ev.contact)}}" target="_blank" rel="noopener">Contact ↗</a>` : ''}}
    </div>
    ${{outreachBlock}}
  </div>`;
}}

function render() {{
  const filtered = getSorted(getFiltered());
  const high   = filtered.filter(e => e.score >= 8);
  const medium = filtered.filter(e => e.score >= 5 && e.score < 8);
  let html = '';
  if (high.length) {{
    html += `<div class="section-header high">
      <h2>High Priority</h2><span class="section-count">${{high.length}}</span></div>
      <div class="events-grid">${{high.map(cardHTML).join('')}}</div>`;
  }}
  if (medium.length) {{
    html += `<div class="section-header medium">
      <h2>Medium Priority</h2><span class="section-count">${{medium.length}}</span></div>
      <div class="events-grid">${{medium.map(cardHTML).join('')}}</div>`;
  }}
  if (!high.length && !medium.length) {{
    html = '<div class="empty-state">No events match the current filter.</div>';
  }}
  document.getElementById('events-container').innerHTML = html;
}}

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    currentFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    render();
  }});
}});

document.getElementById('sort-select').addEventListener('change', e => {{
  currentSort = e.target.value;
  render();
}});

computeStats();
render();
</script>
</body>
</html>
"""


def render_dashboard(events: List[Event], generated_at: str) -> str:
    events_data = []
    for ev in events:
        d = asdict(ev)
        d["date_parsed"] = str(ev.date_parsed) if ev.date_parsed else None
        events_data.append(d)
    events_json = json.dumps(events_data, ensure_ascii=False, indent=2)
    return DASHBOARD_HTML.format(
        generated_at=generated_at,
        events_json=events_json,
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Event Discovery Agent")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Phase 1: Search
    print("\n[PHASE 1] Running searches...")
    search_urls = run_searches()

    # Filter out blocked domains and path patterns
    def is_allowed(u: str) -> bool:
        dom = domain_of(u)
        if dom in BLOCK_DOMAINS:
            return False
        path = urlparse(u).path.lower()
        if any(p in path for p in BLOCK_PATH_PATTERNS):
            return False
        return True

    filtered = [u for u in search_urls if is_allowed(u)]
    blocked  = len(search_urls) - len(filtered)
    if blocked:
        print(f"  Filtered out {blocked} irrelevant URLs")

    # Seeds always go FIRST so they're always scraped regardless of cap
    seen_set = set(filtered)
    urls = [s for s in SEED_URLS if s not in seen_set] + filtered

    print(f"\n  Total unique URLs to scrape: {len(urls)}")

    # Phase 2: Scrape
    print("\n[PHASE 2] Scraping event pages...")
    session  = make_session()
    events: List[Event] = []
    seen_uid: set = set()
    extra_urls: List[str] = []

    for i, url in enumerate(urls[:MAX_SCRAPE_URLS]):
        print(f"  [{i+1:2d}] {url[:75]}")
        ev = scrape_url(url, session)
        if ev is None:
            continue

        # Listing pages return sub-links in scrape_error
        if ev.scrape_error.startswith("listing:"):
            sub_links = ev.scrape_error[len("listing:"):].split("|")
            extra_urls.extend(sub_links)
            continue

        if ev.uid in seen_uid:
            continue
        if not ev.name or len(ev.name) < 4:
            continue

        seen_uid.add(ev.uid)
        events.append(ev)

    # Scrape sub-links from listing pages
    for url in extra_urls[:12]:
        if url in urls:
            continue
        print(f"  [sub] {url[:75]}")
        ev = scrape_url(url, session)
        if ev and ev.uid not in seen_uid and ev.name and len(ev.name) >= 4:
            seen_uid.add(ev.uid)
            events.append(ev)

    print(f"\n  Events extracted: {len(events)}")

    # Phase 3: Score + enrich
    print("\n[PHASE 3] Scoring and generating outreach...")
    scored: List[Event] = []
    for ev in events:
        ev = score_event(ev)
        if ev.score >= 3:
            ev.speaking_title, ev.speaking_topic = generate_speaking_topic(ev)
            ev.outreach_message = generate_outreach(ev)
            scored.append(ev)

    scored.sort(key=lambda e: e.score, reverse=True)
    high_count   = sum(1 for e in scored if e.score >= 8)
    medium_count = sum(1 for e in scored if 5 <= e.score < 8)
    print(f"  Qualifying events (score ≥ 3): {len(scored)}")
    print(f"  High Priority (8-10): {high_count}")
    print(f"  Medium Priority (5-7): {medium_count}")

    # Phase 4: Render dashboard
    print("\n[PHASE 4] Generating dashboard.html...")
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = render_dashboard(scored, generated_at)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Written: {OUTPUT_FILE}")
    except Exception as e:
        fallback = os.path.expanduser("~/Desktop/dashboard.html")
        print(f"  [WARN] Could not write to {OUTPUT_FILE}: {e}")
        print(f"  Writing fallback: {fallback}")
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(html)
        OUTPUT_FILE_FINAL = fallback
    else:
        OUTPUT_FILE_FINAL = OUTPUT_FILE

    webbrowser.open(f"file://{OUTPUT_FILE_FINAL}")

    print("\n" + "=" * 60)
    print("  DONE — Dashboard opened in browser")
    print(f"  High Priority  : {high_count}")
    print(f"  Medium Priority: {medium_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
