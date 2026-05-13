import logging
from datetime import datetime, timezone

from .models import NewsItem

logger = logging.getLogger("news_digest.aggregator")

SOURCE_LABELS = {
    "github_trending": "GitHub Trending",
    "reddit": "Reddit",
    "anthropic": "Anthropic / Claude",
    "openai": "OpenAI",
    "deepseek": "DeepSeek",
}

SOURCE_ORDER = ["openai", "anthropic", "deepseek", "github_trending", "reddit"]


def build_raw_digest(items: list[NewsItem]) -> str:
    if not items:
        return ""

    sorted_items = sorted(
        items,
        key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    parts: list[str] = ["# AI 技术情报日报\n"]

    source_groups: dict[str, list[NewsItem]] = {}
    for item in sorted_items:
        source_groups.setdefault(item.source, []).append(item)

    for source_key in SOURCE_ORDER:
        group = source_groups.get(source_key)
        if not group:
            continue

        label = SOURCE_LABELS.get(source_key, source_key)
        parts.append(f"## {label}\n")
        for item in group:
            pub_str = ""
            if item.published:
                pub_str = f" ({item.published.strftime('%m-%d')})"
            parts.append(f"- [{item.title}]({item.url}){pub_str}")
            if item.summary:
                parts.append(f"  _{item.summary}_")
            parts.append("")
        parts.append("")

    digest = "\n".join(parts)
    logger.info("Raw digest built: %d chars, %d items", len(digest), len(items))
    return digest
