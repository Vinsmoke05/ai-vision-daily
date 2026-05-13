from abc import ABC, abstractmethod

from ..config import Settings
from ..models import NewsItem


class BaseScraper(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    def scrape(self, settings: Settings) -> list[NewsItem]:
        ...
