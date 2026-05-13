import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from .base import BaseScraper
from ..config import Settings
from ..models import NewsItem

logger = logging.getLogger("news_digest.scrapers.opencv")

BLOG_FEED_URL = "https://opencv.org/feed/"
RELEASES_API = "https://api.github.com/repos/opencv/opencv/releases?per_page=5"


class OpenCVScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "opencv"

    def scrape(self, settings: Settings) -> list[NewsItem]:
        items: list[NewsItem] = []

        try:
            items.extend(self._fetch_blog())
        except Exception:
            logger.exception("Failed to scrape OpenCV blog")

        if settings.opencv_check_releases:
            try:
                items.extend(self._fetch_releases())
            except Exception:
                logger.exception("Failed to scrape OpenCV releases")

        return items

    def _fetch_blog(self) -> list[NewsItem]:
        resp = requests.get(BLOG_FEED_URL, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        channel = root.find("channel")
        entries = channel.findall("item") if channel is not None else []
        items: list[NewsItem] = []

        for entry in entries[:10]:
            title = (
                entry.findtext("title", "")
                or entry.findtext("atom:title", "", ns)
            )
            link_el = entry.find("link")
            if link_el is not None:
                url = link_el.get("href") or link_el.text or ""
            else:
                url = entry.findtext("guid", "") or ""

            content = entry.findtext("description", "") or entry.findtext("content", "") or ""
            published_str = entry.findtext("pubDate", "") or entry.findtext("published", "") or entry.findtext("atom:published", "", ns)

            published = None
            if published_str:
                try:
                    from dateutil import parser as dateparser
                    published = dateparser.parse(published_str).replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            items.append(NewsItem(
                source=self.source_name,
                title=title[:200],
                url=url[:500],
                summary=content[:300],
                published=published,
            ))

        logger.info("OpenCV blog: %d items", len(items))
        return items

    def _fetch_releases(self) -> list[NewsItem]:
        now = datetime.now(timezone.utc)
        resp = requests.get(RELEASES_API, timeout=15)
        if resp.status_code == 403:
            logger.warning("GitHub API rate limited, skipping OpenCV releases")
            return []
        resp.raise_for_status()

        releases = resp.json()
        items: list[NewsItem] = []

        for rel in releases[:5]:
            tag = rel.get("tag_name", "")
            name = rel.get("name", "") or tag
            body = (rel.get("body") or "")[:300]
            published_str = rel.get("published_at", "")

            published = None
            if published_str:
                try:
                    published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except Exception:
                    published = now

            items.append(NewsItem(
                source=self.source_name,
                title=f"OpenCV Release: {name}",
                url=rel.get("html_url", ""),
                summary=body[:300],
                published=published,
                tags=["release"],
            ))

        logger.info("OpenCV releases: %d items", len(items))
        return items
