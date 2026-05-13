import logging
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..config import Settings
from ..models import NewsItem

logger = logging.getLogger("news_digest.scrapers.anthropic")

NEWS_URL = "https://www.anthropic.com/news"
RELEASE_NOTES_URL = "https://docs.anthropic.com/en/release-notes"

MONTH_MAP = {
    month: i for i, month in enumerate([
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
    ], start=1)
}


class AnthropicScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "anthropic"

    def scrape(self, settings: Settings) -> list[NewsItem]:
        items: list[NewsItem] = []

        try:
            items.extend(self._fetch_news())
        except Exception:
            logger.exception("Failed to scrape Anthropic news")

        try:
            items.extend(self._fetch_release_notes())
        except Exception:
            logger.exception("Failed to scrape Anthropic release notes")

        return items

    def _fetch_news(self) -> list[NewsItem]:
        resp = requests.get(NEWS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        items: list[NewsItem] = []
        seen_urls: set[str] = set()

        for link in soup.select("a[href*='/news/']"):
            href = link.get("href", "")
            if not href or href == "#":
                continue
            full_url = f"https://www.anthropic.com{href}" if href.startswith("/") else href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            heading = link.select_one("h1, h2, h3, h4, h5, [class*='title'], [class*='heading']")
            title = heading.get_text(strip=True) if heading else ""
            full_text = link.get_text(" ", strip=True)
            published = self._parse_date(full_text)

            if not title:
                title = re.sub(
                    r"^[A-Z][a-z]+\s+\d+,?\s*\d{4}(Announcements|Product|Research|Engineering)?",
                    "", full_text,
                ).strip()
            if not title:
                title = full_text[:200]

            items.append(NewsItem(
                source=self.source_name,
                title=title[:200],
                url=full_url,
                published=published,
            ))

        logger.info("Anthropic news: %d items", len(items))
        return items

    @staticmethod
    def _parse_date(text: str) -> datetime | None:
        match = re.search(r"([A-Z][a-z]+)\s+(\d+),?\s*(\d{4})", text)
        if not match:
            return None
        month = MONTH_MAP.get(match.group(1).lower()[:3])
        if not month:
            return None
        try:
            return datetime(int(match.group(3)), month, int(match.group(2)), tzinfo=timezone.utc)
        except ValueError:
            return None

    def _fetch_release_notes(self) -> list[NewsItem]:
        resp = requests.get(
            RELEASE_NOTES_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        items: list[NewsItem] = []
        seen_dates: set[str] = set()

        for heading in soup.select("h2, h3"):
            text = heading.get_text(strip=True)
            date_match = re.search(r"([A-Z][a-z]+)\s+(\d+),?\s*(\d{4})", text)
            if not date_match:
                continue

            month = MONTH_MAP.get(date_match.group(1).lower()[:3])
            if not month:
                continue

            date_key = f"{date_match.group(3)}-{month:02d}-{int(date_match.group(2)):02d}"
            if date_key in seen_dates:
                continue
            seen_dates.add(date_key)

            try:
                published = datetime(int(date_match.group(3)), month, int(date_match.group(2)), tzinfo=timezone.utc)
            except ValueError:
                published = datetime.now(timezone.utc)

            content_parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ("h2", "h3"):
                    break
                content_parts.append(sibling.get_text(strip=True))
            summary = " ".join(content_parts)[:300]

            items.append(NewsItem(
                source=self.source_name,
                title=f"API Release: {text[:150]}",
                url=RELEASE_NOTES_URL,
                summary=summary,
                published=published,
                tags=["release-notes"],
            ))

        logger.info("Anthropic release notes: %d items", len(items))
        return items[:5]  # latest 5 only
