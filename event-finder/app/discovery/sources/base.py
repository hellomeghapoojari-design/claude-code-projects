from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
from abc import ABC, abstractmethod


@dataclass
class RawEvent:
    uid: str = ""
    name: str = ""
    event_type: str = ""
    date_raw: str = ""
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    location_city: str = ""
    location_state: str = ""
    is_virtual: bool = False
    is_hybrid: bool = False
    organizer: str = ""
    audience_size: Optional[int] = None
    description: str = ""
    url: str = ""
    contact_email: str = ""
    contact_url: str = ""
    source: str = ""
    source_domain: str = ""
    has_speaking: bool = False
    has_partnership: bool = False
    relevance_tags: List[str] = field(default_factory=list)


class BaseSource(ABC):
    @abstractmethod
    def fetch(self) -> List[RawEvent]:
        ...
