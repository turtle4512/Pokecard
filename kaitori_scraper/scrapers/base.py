import asyncio
import random
import logging
from abc import ABC, abstractmethod

from kaitori_scraper.models.data import CollectionItem, MatchResult, Site
from kaitori_scraper.config.settings import (
    MAX_RETRIES, RETRY_BACKOFF_BASE, random_user_agent, DEFAULT_HEADERS,
)


class BaseScraper(ABC):
    site: Site

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def scrape(self, items: list[CollectionItem]) -> list[MatchResult]:
        ...

    async def _delay(self, delay_range: tuple[float, float]) -> None:
        wait = random.uniform(*delay_range)
        self.logger.debug(f"Waiting {wait:.1f}s...")
        await asyncio.sleep(wait)

    def _build_headers(self, referer: str | None = None) -> dict[str, str]:
        headers = {
            "User-Agent": random_user_agent(),
            **DEFAULT_HEADERS,
        }
        if referer:
            headers["Referer"] = referer
        return headers

    async def _retry_operation(self, operation, *args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                self.logger.warning(
                    f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}. "
                    f"Retrying in {wait:.0f}s..."
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
                else:
                    self.logger.error(f"All {MAX_RETRIES} attempts failed.")
                    raise
