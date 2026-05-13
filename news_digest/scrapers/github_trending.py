import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..config import Settings
from ..models import NewsItem

logger = logging.getLogger("news_digest.scrapers.github")

AI_KEYWORDS = {
    "llm", "large-language-model", "gpt", "claude", "agent",
    "mcp", "model-context-protocol", "ai-coding", "code-generation",
    "copilot", "function-calling", "tool-use", "prompt-engineering",
    "rag", "ai-agent", "chatgpt", "openai", "anthropic",
    "deepseek", "langchain", "ai-tool", "ai-framework",
    "vector-database", "embedding", "ai-sdk", "ai-api",
    "autonomous-agent", "multi-agent", "workflow-engine",
    "ai-assistant", "ai-plugin", "ai-extension",
}


class GitHubTrendingScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "github_trending"

    def scrape(self, settings: Settings) -> list[NewsItem]:
        items: list[NewsItem] = []
        today = datetime.now(timezone.utc)

        for lang in settings.gh_trending_languages:
            try:
                items.extend(self._fetch_trending(lang, today))
            except Exception:
                logger.exception("Failed to scrape GitHub trending for %s", lang)

        return items

    def _fetch_trending(self, language: str, today: datetime) -> list[NewsItem]:
        url = f"https://github.com/trending/{language}?since=daily"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.select("article.Box-row")
        items: list[NewsItem] = []

        for article in articles:
            h2 = article.select_one("h2")
            if not h2:
                continue

            repo_full = h2.get_text(strip=True).replace(" ", "")
            repo_url = f"https://github.com/{repo_full}"

            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            topic_els = article.select("a.topic-tag")
            topics = [t.get_text(strip=True) for t in topic_els]

            if not self._is_relevant(description, topics):
                continue

            items.append(NewsItem(
                source=self.source_name,
                title=f"[{language}] {repo_full}",
                url=repo_url,
                summary=description[:300],
                published=today,
                tags=topics,
            ))

        logger.info("GitHub Trending (%s): %d relevant items", language, len(items))
        return items

    @staticmethod
    def _is_relevant(description: str, topics: list[str]) -> bool:
        combined = f"{description} {' '.join(topics)}".lower()
        return any(kw in combined for kw in AI_KEYWORDS)
