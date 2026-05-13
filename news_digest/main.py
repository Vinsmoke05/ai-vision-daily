import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .cache import NewsCache
from .config import Settings
from .logger_setup import setup_logging
from .scrapers import (
    DeepSeekScraper,
    GitHubTrendingScraper,
    OpenCVScraper,
    RedditScraper,
)

logger = logging.getLogger("news_digest")


def main() -> int:
    settings = Settings()
    setup_logging(settings.log_dir)

    logger.info("=" * 50)
    logger.info("Starting AI Vision Daily Digest")
    logger.info("=" * 50)

    scrapers = [
        GitHubTrendingScraper(),
        RedditScraper(),
        OpenCVScraper(),
        DeepSeekScraper(),
    ]

    all_items: list = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        fut_to_scraper = {pool.submit(s.scrape, settings): s for s in scrapers}
        for fut in as_completed(fut_to_scraper):
            scraper = fut_to_scraper[fut]
            try:
                items = fut.result()
                all_items.extend(items)
                logger.info(
                    "%s: collected %d items",
                    scraper.source_name, len(items),
                )
            except Exception:
                logger.exception(
                    "%s: scraper failed", scraper.source_name,
                )

    logger.info("Total raw items collected: %d", len(all_items))

    cache = NewsCache(settings.cache_db_path)
    new_items = cache.filter_new(all_items)
    logger.info("New items after dedup: %d", len(new_items))

    if new_items:
        cache.bulk_upsert(new_items)

    if not new_items:
        logger.info("No new items found, skipping summary and publish.")
        return 0

    from .aggregator import build_raw_digest
    raw_digest = build_raw_digest(new_items)
    logger.info("Raw digest built (%d chars)", len(raw_digest))

    from .summarizer import summarize
    final_digest = summarize(raw_digest, settings)

    from .publisher import publish
    if final_digest:
        success = publish(final_digest, settings)
    else:
        logger.warning("LLM summary failed, falling back to raw digest")
        success = publish("[RAW - LLM 不可用]\n\n" + raw_digest, settings)

    if success:
        logger.info("Daily digest published successfully!")
        return 0
    else:
        logger.error("Failed to publish digest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
