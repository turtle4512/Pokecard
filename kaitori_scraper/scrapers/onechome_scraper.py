"""
1-chome.com scraper — SPA site, Playwright browser automation.

Strategy: search by Japanese keyword per product, parse rendered DOM.
Selectors are tentative and may need F12 verification on first run.
"""

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
    random_user_agent,
    DEFAULT_HEADERS,
)

logger = logging.getLogger(__name__)


class OneChomeScraper(BaseScraper):
    site = Site.ONECHOME

    async def scrape(self, items: list[CollectionItem]) -> list[MatchResult]:
        results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random_user_agent(),
                locale="ja-JP",
                extra_http_headers=DEFAULT_HEADERS,
            )
            page = await context.new_page()

            await page.goto(ONECHOME_BASE_URL, wait_until="networkidle")
            logger.info("Loaded 1-chome.com homepage")

            for item in items:
                match = await self._search_item(page, item)
                results.append(match)

                if match.product:
                    logger.info(
                        f"  [{item.id}] {item.name_jp} -> {match.product.name} "
                        f"(score={match.score:.2f}, ¥{match.product.price_low:,})"
                    )
                else:
                    logger.warning(f"  [{item.id}] {item.name_jp} -> NO MATCH")

                await self._delay(ONECHOME_SEARCH_DELAY)

            await browser.close()

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
        # Find search input
        search_selectors = ONECHOME_SELECTORS["search_input"].split(", ")
        search_input = None

        for selector in search_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=3000):
                    search_input = locator
                    break
            except Exception:
                continue

        if search_input is None:
            raise RuntimeError("Could not find search input on 1-chome.com")

        await search_input.fill("")
        await search_input.fill(keyword)
        await search_input.press("Enter")

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        return await self._parse_search_results(page)

    async def _parse_search_results(self, page: Page) -> list[ScrapedProduct]:
        products = []

        card_selectors = ONECHOME_SELECTORS["product_card"].split(", ")

        for selector in card_selectors:
            cards = page.locator(selector)
            count = await cards.count()
            if count > 0:
                logger.debug(f"  Found {count} cards with selector '{selector}'")
                for i in range(count):
                    card = cards.nth(i)
                    try:
                        product = await self._parse_single_card(card)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.debug(f"  Failed to parse card {i}: {e}")
                if products:
                    return products

        # Fallback: parse from page text
        return await self._parse_from_page_text(page)

    async def _parse_single_card(self, card) -> ScrapedProduct | None:
        text = await card.inner_text()
        if not text.strip():
            return None

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        name = None
        for line in lines:
            if len(line) > 3 and "カート" not in line:
                name = line
                break

        if not name:
            return None

        price_match = re.search(ONECHOME_PRICE_PATTERN, text)
        if not price_match:
            return None

        price = int(price_match.group(1).replace(",", ""))

        jan_match = re.search(r"(?:JAN|jan)[:\s]*(\d{13})", text)
        jan_code = jan_match.group(1) if jan_match else None

        condition = "新品" if "新品" in text else ("中古" if "中古" in text else None)

        return ScrapedProduct(
            site=Site.ONECHOME,
            name=name,
            price_low=price,
            jan_code=jan_code,
            condition=condition,
        )

    async def _parse_from_page_text(self, page: Page) -> list[ScrapedProduct]:
        """Fallback: extract from raw page text when card selectors fail."""
        logger.debug("Falling back to full-page text parsing")
        products = []

        try:
            text = await page.inner_text("body")
        except Exception:
            return products

        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "【" in line and ("BOX" in line or "セット" in line):
                context = "\n".join(lines[max(0, i - 2):i + 5])
                price_match = re.search(ONECHOME_PRICE_PATTERN, context)
                if price_match:
                    price = int(price_match.group(1).replace(",", ""))
                    products.append(ScrapedProduct(
                        site=Site.ONECHOME,
                        name=line.strip(),
                        price_low=price,
                    ))

        return products
