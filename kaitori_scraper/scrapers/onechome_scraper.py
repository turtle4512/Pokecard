"""
1-chome.com scraper — SPA site (Element Plus / Vue.js), Playwright browser automation.

Strategy: search by Japanese keyword per product, parse rendered DOM.
Uses multiple browser tabs for parallel searching to improve speed.
Selectors confirmed via Playwright DOM inspection.

Card text structure:
    【S＆V】クレイバースト BOX
    JAN: 4521329346182
    ポケモンカード
    ※シュリンク付き、新品未開封
    新品
    ¥11,000
    カートに入れる
"""

import asyncio
import re
import logging
from playwright.async_api import async_playwright, Page

from kaitori_scraper.scrapers.base import BaseScraper
from kaitori_scraper.models.data import CollectionItem, ScrapedProduct, MatchResult, Site
from kaitori_scraper.matcher.fuzzy_match import find_best_match
from kaitori_scraper.config.settings import (
    ONECHOME_BASE_URL,
    ONECHOME_SEARCH_DELAY,
    ONECHOME_PRICE_PATTERN,
    ONECHOME_SELECTORS,
    ONECHOME_CONCURRENT_TABS,
    random_user_agent,
    DEFAULT_HEADERS,
)

logger = logging.getLogger(__name__)


class OneChomeScraper(BaseScraper):
    site = Site.ONECHOME

    async def scrape(self, items: list[CollectionItem]) -> list[MatchResult]:
        num_tabs = min(ONECHOME_CONCURRENT_TABS, len(items))

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random_user_agent(),
                locale="ja-JP",
                extra_http_headers=DEFAULT_HEADERS,
            )

            # Split items into chunks for each tab
            chunks = [[] for _ in range(num_tabs)]
            for i, item in enumerate(items):
                chunks[i % num_tabs].append((i, item))

            # Create pages and navigate to homepage in parallel
            pages = []
            for _ in range(num_tabs):
                page = await context.new_page()
                pages.append(page)

            await asyncio.gather(*(
                page.goto(ONECHOME_BASE_URL, wait_until="networkidle")
                for page in pages
            ))
            logger.info(f"Loaded 1-chome.com homepage on {num_tabs} tabs")

            # Run tab workers in parallel
            chunk_results = await asyncio.gather(*(
                self._tab_worker(pages[tab_idx], chunks[tab_idx], tab_idx)
                for tab_idx in range(num_tabs)
            ))

            await browser.close()

        # Merge results back in original item order
        indexed_results: dict[int, MatchResult] = {}
        for results in chunk_results:
            indexed_results.update(results)

        return [indexed_results[i] for i in range(len(items))]

    async def _tab_worker(
        self, page: Page, indexed_items: list[tuple[int, CollectionItem]], tab_id: int
    ) -> dict[int, MatchResult]:
        """Process a chunk of items on a single browser tab."""
        results: dict[int, MatchResult] = {}

        for idx, item in indexed_items:
            match = await self._search_item(page, item)
            results[idx] = match

            if match.product:
                logger.info(
                    f"  [{item.id}] {item.name_jp} -> {match.product.name} "
                    f"(score={match.score:.2f}, ¥{match.product.price_low:,})"
                )
            else:
                logger.warning(f"  [{item.id}] {item.name_jp} -> NO MATCH")

            await self._delay(ONECHOME_SEARCH_DELAY)

        return results

    async def _search_item(self, page: Page, item: CollectionItem) -> MatchResult:
        all_products: list[ScrapedProduct] = []

        for keyword in item.search_keywords:
            try:
                products = await self._perform_search(page, keyword)
                all_products.extend(products)
                if products:
                    logger.debug(f"  Keyword '{keyword}': found {len(products)} results")
                    break
            except Exception as e:
                logger.warning(f"  Search failed for '{keyword}': {e}")
                continue

        if not all_products:
            return MatchResult(
                collection_item=item,
                product=None,
                score=0.0,
                matched_keyword=None,
                site=Site.ONECHOME,
            )

        return find_best_match(item, all_products, Site.ONECHOME)

    async def _perform_search(self, page: Page, keyword: str) -> list[ScrapedProduct]:
        search_input = page.locator(ONECHOME_SELECTORS["search_input"]).first
        search_btn = page.locator(ONECHOME_SELECTORS["search_button"]).first

        if not await search_input.is_visible(timeout=5000):
            raise RuntimeError("Search input not visible")

        await search_input.fill("")
        await search_input.fill(keyword)
        await search_btn.click()

        await page.wait_for_load_state("domcontentloaded")
        # Smart wait: wait for product cards to appear, or timeout quickly if none
        try:
            await page.locator(ONECHOME_SELECTORS["product_card"]).first.wait_for(
                state="visible", timeout=3000
            )
        except Exception:
            # No results appeared within 3s — likely no matches
            pass

        return await self._parse_search_results(page)

    async def _parse_search_results(self, page: Page) -> list[ScrapedProduct]:
        products = []

        cards = page.locator(ONECHOME_SELECTORS["product_card"])
        count = await cards.count()
        logger.debug(f"  Found {count} commodity-item cards")

        for i in range(count):
            card = cards.nth(i)
            try:
                product = await self._parse_single_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"  Failed to parse card {i}: {e}")

        return products

    async def _parse_single_card(self, card) -> ScrapedProduct | None:
        """
        Parse card inner text. Expected format:
            【S＆V】クレイバースト BOX
            JAN: 4521329346182
            ポケモンカード
            ※シュリンク付き、新品未開封
            新品
            ¥11,000
            カートに入れる
        """
        text = await card.inner_text()
        if not text.strip():
            return None

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Product name: first line with 【 prefix or substantial length
        name = None
        for line in lines:
            if "【" in line or (len(line) > 5 and "カート" not in line and "JAN" not in line
                               and "¥" not in line and "※" not in line):
                name = line
                break

        if not name:
            return None

        # Price: ¥XX,XXX
        price_match = re.search(ONECHOME_PRICE_PATTERN, text)
        if not price_match:
            return None

        price = int(price_match.group(1).replace(",", ""))

        # JAN code
        jan_match = re.search(r"JAN[:\s]*(\d{13})", text)
        jan_code = jan_match.group(1) if jan_match else None

        # Condition
        condition = "新品" if "新品" in text else ("中古" if "中古" in text else None)

        return ScrapedProduct(
            site=Site.ONECHOME,
            name=name,
            price_low=price,
            jan_code=jan_code,
            condition=condition,
        )
