import logging
from datetime import datetime, timezone

import requests

from .base import BaseScraper
from ..config import Settings
from ..models import NewsItem

logger = logging.getLogger("news_digest.scrapers.openai")

RELEASES_API = "https://api.github.com/repos/openai/openai-python/releases?per_page=5"


class OpenAIScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "openai"

    def scrape(self, settings: Settings) -> list[NewsItem]:
        items: list[NewsItem] = []

        try:
            items.extend(self._fetch_releases())
        except Exception:
            logger.exception("Failed to scrape OpenAI releases")

        return items

    def _fetch_releases(self) -> list[NewsItem]:
        resp = requests.get(RELEASES_API, timeout=15)
        if resp.status_code == 403:
            logger.warning("GitHub API rate limited, skipping OpenAI releases")
            return []
        resp.raise_for_status()

        releases = resp.json()
        items: list[NewsItem] = []

        for rel in releases:
            tag = rel.get("tag_name", "")
            name = rel.get("name", "") or tag
            body = (rel.get("body") or "")[:300]
            published_str = rel.get("published_at", "")

            published = None
            if published_str:
                try:
                    published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except Exception:
                    published = datetime.now(timezone.utc)

            # Extract feature highlights from body
            summary = body
            if body:
                # Look for the first Features section
                for line in body.split("\n"):
                    if line.startswith("- ") or line.startswith("* "):
                        summary = line.strip()[:300]
                        break

            items.append(NewsItem(
                source=self.source_name,
                title=f"Python SDK {name}",
                url=rel.get("html_url", ""),
                summary=summary,
                published=published,
                tags=["sdk-release"],
            ))

        logger.info("OpenAI releases: %d items", len(items))
        return items
