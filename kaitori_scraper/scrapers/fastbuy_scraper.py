"""
Fastbuy.jp scraper — SSR site, httpx + BeautifulSoup.

Strategy: crawl all 7 category pages -> build product index -> fuzzy match.
"""

import asyncio
import re
import logging
import httpx
from bs4 import BeautifulSoup

from kaitori_scraper.scrapers.base import BaseScraper
from kaitori_scraper.models.data import CollectionItem, ScrapedProduct, MatchResult, Site
from kaitori_scraper.matcher.fuzzy_match import find_best_match
from kaitori_scraper.config.settings import (
    FASTBUY_TOTAL_PAGES,
    FASTBUY_REQUEST_DELAY,
    FASTBUY_PRICE_PATTERN,
    FASTBUY_SELECTORS,
    fastbuy_page_url,
)

logger = logging.getLogger(__name__)


class FastbuyScraper(BaseScraper):
    site = Site.FASTBUY

    async def scrape(self, items: list[CollectionItem]) -> list[MatchResult]:
        products = await self._crawl_all_pages()
        logger.info(f"Crawled {len(products)} products from fastbuy.jp")

        results = []
        for item in items:
            match = find_best_match(item, products, Site.FASTBUY)
            if match.product:
                logger.info(
                    f"  [{item.id}] {item.name_jp} -> {match.product.name} "
                    f"(score={match.score:.2f}, ¥{match.product.price_low:,})"
                )
            else:
                logger.warning(
                    f"  [{item.id}] {item.name_jp} -> NO MATCH (best={match.score:.2f})"
                )
            results.append(match)

        return results

    async def _crawl_all_pages(self) -> list[ScrapedProduct]:
        all_products: list[ScrapedProduct] = []

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # Fetch all pages concurrently
            urls = [fastbuy_page_url(page) for page in range(1, FASTBUY_TOTAL_PAGES + 1)]
            logger.info(f"Crawling {FASTBUY_TOTAL_PAGES} pages concurrently...")

            async def _fetch_one(page_num: int, url: str) -> list[ScrapedProduct]:
                # Stagger requests slightly to avoid burst
                await asyncio.sleep(0.2 * (page_num - 1))
                response = await self._retry_operation(
                    self._fetch_page, client, url, "https://fastbuy.jp/"
                )
                products = self._parse_page(response.text, page_num)
                logger.info(f"  Page {page_num}: found {len(products)} products")
                return products

            results = await asyncio.gather(*(
                _fetch_one(i + 1, url) for i, url in enumerate(urls)
            ))

            for products in results:
                all_products.extend(products)

        return all_products

    async def _fetch_page(
        self, client: httpx.AsyncClient, url: str, referer: str
    ) -> httpx.Response:
        headers = self._build_headers(referer=referer)
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response

    def _parse_page(self, html: str, page_num: int) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "lxml")
        products = []

        cards = soup.select(FASTBUY_SELECTORS["product_card"])
        for card in cards:
            product = self._parse_product_card(card)
            if product:
                products.append(product)

        return products

    def _parse_product_card(self, card) -> ScrapedProduct | None:
        # Extract URL and product ID
        href = card.get("href", "")
        product_url = f"https://fastbuy.jp{href}" if href.startswith("/") else href
        product_id = None
        id_match = re.search(r"id=(\d+)", href)
        if id_match:
            product_id = id_match.group(1)

        # Extract text content
        all_text = card.get_text(separator="\n", strip=True)
        text_lines = [line.strip() for line in all_text.split("\n") if line.strip()]

        # Product name: filter out short labels (色, 強化, etc.)
        name_candidates = [t for t in text_lines if len(t) > 5]
        if not name_candidates:
            return None
        product_name = name_candidates[0]

        # 買取強化 flag
        is_enhanced = "強化" in all_text

        # Extract price
        # Regex has 4 groups: (¥low, ¥high, 円low, 円high)
        price_matches = re.findall(FASTBUY_PRICE_PATTERN, all_text)
        if not price_matches:
            return None

        price_low = None
        price_high = None
        for match in price_matches:
            # Groups 0,1 = ¥ prefix pattern; Groups 2,3 = 円 suffix pattern
            low_str = (match[0] or match[2]).replace(",", "")
            high_str = (match[1] or match[3]).replace(",", "")
            if low_str and low_str.isdigit():
                price_low = int(low_str)
                if high_str and high_str.isdigit():
                    price_high = int(high_str)
                break

        if price_low is None:
            return None

        return ScrapedProduct(
            site=Site.FASTBUY,
            name=product_name,
            price_low=price_low,
            price_high=price_high,
            product_url=product_url,
            product_id=product_id,
            is_enhanced=is_enhanced,
        )
