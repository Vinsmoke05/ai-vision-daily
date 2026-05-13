import logging
import time
from datetime import datetime, timezone

import requests

from .base import BaseScraper
from ..config import Settings
from ..models import NewsItem

logger = logging.getLogger("news_digest.scrapers.reddit")

CV_KEYWORDS_LOWER = {
    "computer vision", "deep learning", "object detection", "yolo",
    "ocr", "image processing", "stable diffusion", "diffusion model",
    "llm", "vision transformer", "segmentation", "detection",
    "face recognition", "visual slam", "3d vision",
    "neural network", "opencv", "machine learning",
    "robotics", "autonomous", "self-driving", "cnn", "transformer",
    "clip", "open vocabulary", "foundation model", "slam",
    "depth estimation", "nerf", "gaussian splatting",
}


class RedditScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "reddit"

    def scrape(self, settings: Settings) -> list[NewsItem]:
        items: list[NewsItem] = []

        for subreddit in settings.reddit_subreddits:
            try:
                items.extend(self._fetch_subreddit(subreddit))
                time.sleep(2)
            except Exception:
                logger.exception("Failed to scrape r/%s", subreddit)

        return items

    def _fetch_subreddit(self, subreddit: str) -> list[NewsItem]:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
        resp = requests.get(
            url,
            headers={"User-Agent": "news_digest/1.0"},
            timeout=15,
        )
        if resp.status_code == 429:
            logger.warning("Rate limited on r/%s, skipping", subreddit)
            return []
        resp.raise_for_status()

        data = resp.json()
        children = data.get("data", {}).get("children", [])
        items: list[NewsItem] = []

        for child in children:
            post = child.get("data", {})
            title = post.get("title", "")
            selftext = post.get("selftext", "") or ""
            score = post.get("score", 0)
            permalink = post.get("permalink", "")
            full_url = f"https://www.reddit.com{permalink}"
            created = post.get("created_utc", 0)

            combined = f"{title} {selftext}".lower()
            if not any(kw in combined for kw in CV_KEYWORDS_LOWER):
                continue
            if score < 5:
                continue

            items.append(NewsItem(
                source=self.source_name,
                title=title[:200],
                url=full_url,
                summary=(selftext[:300] if selftext else title)[:300],
                published=datetime.fromtimestamp(created, tz=timezone.utc) if created else None,
                tags=[subreddit],
            ))

        logger.info("Reddit r/%s: %d relevant items (filtered from %d)", subreddit, len(items), len(children))
        return items
