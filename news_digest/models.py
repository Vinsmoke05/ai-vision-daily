from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsItem:
    source: str
    title: str
    url: str
    summary: str = ""
    published: datetime | None = None
    tags: list[str] = field(default_factory=list)
    score: int = 0

    @property
    def item_id(self) -> str:
        import hashlib
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]
