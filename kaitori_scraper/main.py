"""
ポケモンカード買取価格スクレイパー

Usage:
    python -m kaitori_scraper.main                    # Both sites
    python -m kaitori_scraper.main --fastbuy-only     # Fastbuy only
    python -m kaitori_scraper.main --onechome-only    # 1-chome only
    python -m kaitori_scraper.main --items 5,8,14     # Specific items
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from kaitori_scraper.config.collection import get_collection_by_ids
from kaitori_scraper.scrapers.fastbuy_scraper import FastbuyScraper
from kaitori_scraper.scrapers.onechome_scraper import OneChomeScraper
from kaitori_scraper.output.comparator import compare_results
from kaitori_scraper.output.report import save_reports, generate_text_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ポケモンカード買取価格スクレイパー"
    )
    parser.add_argument(
        "--fastbuy-only",
        action="store_true",
        help="Only scrape fastbuy.jp (no Playwright needed)",
    )
    parser.add_argument(
        "--onechome-only",
        action="store_true",
        help="Only scrape 1-chome.com",
    )
    parser.add_argument(
        "--items",
        type=str,
        default=None,
        help="Comma-separated item IDs (e.g. 5,8,14)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory for output reports (default: current dir)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("main")

    # Parse item IDs
    item_ids = None
    if args.items:
        item_ids = [int(x.strip()) for x in args.items.split(",")]

    items = get_collection_by_ids(item_ids)
    logger.info(f"Target: {len(items)} collection items")

    timestamp = datetime.now()
    fastbuy_results = []
    onechome_results = []

    run_fastbuy = not args.onechome_only
    run_onechome = not args.fastbuy_only

    async def _scrape_fastbuy():
        logger.info("=" * 40)
        logger.info("Starting fastbuy.jp scrape...")
        logger.info("=" * 40)
        return await FastbuyScraper().scrape(items)

    async def _scrape_onechome():
        logger.info("=" * 40)
        logger.info("Starting 1-chome.com scrape...")
        logger.info("=" * 40)
        return await OneChomeScraper().scrape(items)

    if run_fastbuy and run_onechome:
        fastbuy_results, onechome_results = await asyncio.gather(
            _scrape_fastbuy(), _scrape_onechome()
        )
    elif run_fastbuy:
        fastbuy_results = await _scrape_fastbuy()
    elif run_onechome:
        onechome_results = await _scrape_onechome()

    # Compare and report
    comparison = compare_results(items, fastbuy_results, onechome_results)

    text_report = generate_text_report(comparison, timestamp)
    print("\n" + text_report)

    text_path, csv_path = save_reports(comparison, args.output_dir, timestamp)
    logger.info(f"Text report saved: {text_path}")
    logger.info(f"CSV report saved: {csv_path}")


def entry() -> None:
    # Use default ProactorEventLoop on Windows (required by Playwright)
    asyncio.run(main())


if __name__ == "__main__":
    entry()
