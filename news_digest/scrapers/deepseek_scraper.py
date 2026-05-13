import logging
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..config import Settings
from ..models import NewsItem

logger = logging.getLogger("news_digest.scrapers.deepseek")

SITEMAP_URL = "https://api-docs.deepseek.com/sitemap.xml"
BASE_URL = "https://api-docs.deepseek.com"


class DeepSeekScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "deepseek"

    def scrape(self, settings: Settings) -> list[NewsItem]:
        try:
            news_urls = self._fetch_news_urls_from_sitemap()
        except Exception:
            logger.exception("Failed to fetch DeepSeek sitemap")
            return []

        if not news_urls:
            logger.warning("No DeepSeek news URLs found")
            return []

        logger.info("Found %d DeepSeek news articles", len(news_urls))

        items: list[NewsItem] = []
        for url, pub_date in news_urls[:5]:
            try:
                items.append(self._fetch_article(url, pub_date))
            except Exception:
                logger.debug("Failed to fetch DeepSeek article %s", url)

        logger.info("DeepSeek: %d items collected", len(items))
        return items

    def _fetch_news_urls_from_sitemap(self) -> list[tuple[str, datetime]]:
        resp = requests.get(SITEMAP_URL, timeout=15)
        resp.raise_for_status()

        root = BeautifulSoup(resp.text, "xml")
        urls: list[tuple[str, datetime]] = []

        for loc in root.select("url > loc"):
            url = loc.get_text(strip=True)
            if "/news/news" not in url:
                continue

            # Extract date from URL: /news/newsYYMMDD or /news/newsMMDD
            match = re.search(r"/news/news(\d{2,6})/?$", url)
            if not match:
                continue

            code = match.group(1)
            pub_date = self._parse_date_from_code(code)
            urls.append((url, pub_date))

        urls.sort(key=lambda x: x[1], reverse=True)
        return urls

    @staticmethod
    def _parse_date_from_code(code: str) -> datetime:
        now = datetime.now(timezone.utc)
        if len(code) == 6:
            year = int(code[:2]) + 2000
            month = int(code[2:4])
            day = int(code[4:6])
        elif len(code) == 4:
            # 2024 pattern: MMDD, no year in code
            year = 2024
            month = int(code[:2])
            day = int(code[2:4])
        else:
            return now

        try:
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return now

    def _fetch_article(self, url: str, pub_date: datetime) -> NewsItem:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        title_el = soup.select_one("h1") or soup.select_one("title")
        title = title_el.get_text(strip=True) if title_el else "DeepSeek News"

        # Extract main content
        article = soup.select_one("article, main, .markdown, .docMainContainer")
        summary = ""
        if article:
            # Get first meaningful paragraph
            for p in article.select("p"):
                text = p.get_text(strip=True)
                if len(text) > 20:
                    summary = text[:300]
                    break

        return NewsItem(
            source=self.source_name,
            title=title[:200],
            url=url,
            summary=summary,
            published=pub_date,
        )
