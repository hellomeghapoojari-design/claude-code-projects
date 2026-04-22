"""
Scores RawEvents for relevance to an Indian corporate/motivational speaker.
Adapted from agent.py scoring logic with Indian corporate context.
"""
import re
import datetime
from app.discovery.sources.base import RawEvent

ICP_SIGNALS = [
    "corporate", "enterprise", "organisation", "organization",
    "hr ", "human resources", "cto", "ceo", "vp ", "director", "manager",
    "team building", "team-building", "leadership", "motivation", "motivational",
    "culture", "organizational", "workforce", "employee engagement",
    "talent", "l&d", "learning and development", "training", "coaching",
    "mindset", "high performance", "peak performance", "productivity",
    "change management", "transformation", "wellbeing", "mental health",
]

SPEAKING_SIGNALS = [
    "call for speakers", "cfp", "call for proposals", "speaking opportunity",
    "submit a talk", "apply to speak", "speaker application", "speak at",
    "call for presentations", "keynote", "panelist", "panel discussion",
    "masterclass", "workshop facilitator",
]

PARTNERSHIP_SIGNALS = [
    "sponsor", "partnership", "exhibitor", "partner opportunity",
    "booth", "become a partner", "associate partner",
]

URL_SPEAKING_SIGNALS = [
    "call-for-speakers", "cfp", "speak-at", "speaking",
    "call-for-proposals", "submit-a-talk", "apply-to-speak", "keynote",
]
URL_PARTNERSHIP_SIGNALS = ["sponsor", "partnership", "exhibitor", "partner"]

HIGH_AUTH_DOMAINS = {
    "nasscom.in": 9, "cii.in": 9, "ficci.in": 9,
    "10times.com": 8, "townscript.com": 7,
    "lu.ma": 8, "luma.com": 8,
    "eventbrite.com": 6,
    "shrmindia.org": 8, "peoplematter.in": 7,
    "indiahrforum.in": 8, "nhrd.net": 8,
    "tiecon.org": 7, "indialeadershipsummit.com": 8,
}

INDIA_CITIES = [
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai",
    "pune", "kolkata", "ahmedabad", "surat", "jaipur", "lucknow",
    "noida", "gurgaon", "gurugram", "chandigarh", "kochi", "indore",
]


def _detect_signals(text: str) -> tuple[bool, bool]:
    tl = text.lower()
    has_speaking = any(s in tl for s in SPEAKING_SIGNALS)
    has_partnership = any(s in tl for s in PARTNERSHIP_SIGNALS)
    return has_speaking, has_partnership


def score_event(ev: RawEvent) -> tuple[int, dict]:
    today = datetime.date.today()
    text = f"{ev.name} {ev.description} {ev.organizer} {ev.event_type}".lower()
    url_lower = ev.url.lower().replace("-", " ").replace("/", " ")
    full_text = text + " " + url_lower

    # Boost signals from URL
    has_speaking = ev.has_speaking or any(s in url_lower for s in URL_SPEAKING_SIGNALS)
    has_partnership = ev.has_partnership or any(s in url_lower for s in URL_PARTNERSHIP_SIGNALS)

    # ICP fit — how well this event's audience matches the influencer's target
    hits = sum(1 for s in ICP_SIGNALS if s in full_text)
    icp_table = [1, 1, 3, 5, 6, 7, 8, 9, 10, 10, 10]
    icp = float(icp_table[min(hits, 10)])

    # Bonus for India-specific city mentions
    if any(city in full_text for city in INDIA_CITIES):
        icp = min(10.0, icp + 1.5)

    # Authority — domain prestige + event prestige signals
    authority = float(HIGH_AUTH_DOMAINS.get(ev.source_domain, 4))
    prestige_signals = ["annual", "national", "international", "summit", "forum", "conclave", "congress"]
    if any(w in ev.name.lower() for w in prestige_signals):
        authority = min(10.0, authority + 1)

    # Lead potential — does this event offer speaking or attendance value?
    lead = 2.0 if ev.url else 0.0
    if has_speaking:
        lead += 5
    if has_partnership:
        lead += 3
    m = re.search(r'(\d[\d,]+)\s*(attendees|participants|professionals|delegates|registrations)', full_text)
    if m:
        n = int(m.group(1).replace(",", ""))
        lead += 3 if n >= 500 else (2 if n >= 200 else 1)
    lead = min(10.0, lead)

    # Deadline proximity
    if ev.date_start:
        delta = (ev.date_start - today).days
        if delta < 0:
            return 0, {}
        if delta <= 30:
            deadline = 10.0
        elif delta <= 60:
            deadline = 8.0
        elif delta <= 90:
            deadline = 6.0
        elif delta <= 180:
            deadline = 4.0
        else:
            deadline = 2.0
    else:
        deadline = 3.0

    breakdown = {
        "icp": round(icp, 1),
        "authority": round(authority, 1),
        "lead": round(lead, 1),
        "deadline": round(deadline, 1),
    }
    raw = icp * 0.35 + authority * 0.25 + lead * 0.25 + deadline * 0.15
    final_score = max(1, min(10, round(raw)))
    return final_score, breakdown


def build_tags(ev: RawEvent) -> list[str]:
    text = f"{ev.name} {ev.description} {ev.event_type}".lower()
    tag_map = {
        "leadership": ["leadership", "leader", "management"],
        "team building": ["team building", "team-building", "teamwork"],
        "motivation": ["motivation", "motivational", "mindset", "inspire"],
        "hr & l&d": ["hr ", "human resources", "l&d", "learning", "training"],
        "corporate culture": ["culture", "employee engagement", "wellbeing"],
        "coaching": ["coaching", "coach", "mentoring"],
        "keynote": ["keynote", "call for speakers", "cfp"],
    }
    tags = []
    for tag, signals in tag_map.items():
        if any(s in text for s in signals):
            tags.append(tag)
    return tags
