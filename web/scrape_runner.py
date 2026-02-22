"""
Background scrape orchestration and state management.

Runs async scrapers in a dedicated background thread with its own event loop,
captures progress via logging, and exposes state for the Flask web frontend.
"""

import asyncio
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime

from kaitori_scraper.config.collection import get_collection_by_ids
from kaitori_scraper.scrapers.fastbuy_scraper import FastbuyScraper
from kaitori_scraper.scrapers.onechome_scraper import OneChomeScraper
from kaitori_scraper.output.comparator import compare_results
from kaitori_scraper.output.report import generate_text_report, generate_csv_report
from kaitori_scraper.models.data import ComparisonRow

# ── Background event loop ──

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None


def init_background_loop() -> None:
    global _loop, _thread
    _loop = asyncio.new_event_loop()
    _thread = threading.Thread(target=_loop.run_forever, daemon=True)
    _thread.start()


# ── Shared state ──

_lock = threading.Lock()
_state: "ScrapeState | None" = None


@dataclass
class ScrapeState:
    status: str = "idle"  # idle | running | completed | error
    mode: str = ""
    progress: float = 0.0
    phase: str = ""
    log_lines: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    results: list[ComparisonRow] = field(default_factory=list)
    error_message: str | None = None
    csv_content: str | None = None
    text_content: str | None = None
    total_items: int = 18


def get_state() -> ScrapeState:
    global _state
    with _lock:
        if _state is None:
            _state = ScrapeState()
        return _state


def _update(**kwargs) -> None:
    with _lock:
        state = get_state()
        for k, v in kwargs.items():
            setattr(state, k, v)


# ── Progress capture ──

class _ProgressHandler(logging.Handler):
    """Intercept scraper log messages to update progress state."""

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        with _lock:
            state = get_state()
            state.log_lines.append(msg)

            # Parse fastbuy page progress: "Crawling page 3/7"
            m = re.search(r"Crawling page (\d+)/(\d+)", msg)
            if m:
                page, total = int(m.group(1)), int(m.group(2))
                if state.mode == "fastbuy":
                    state.progress = page / total * 0.9
                elif state.mode == "both":
                    state.progress = 0.3 * (page / total)

            # Parse 1-chome item progress: "[5]"
            m = re.search(r"\[(\d+)\]", msg)
            if m and "1-chome" in state.phase:
                item_num = int(m.group(1))
                frac = item_num / state.total_items
                if state.mode == "onechome":
                    state.progress = frac * 0.9
                elif state.mode == "both":
                    state.progress = 0.3 + 0.65 * frac


# ── Async scrape orchestration ──

async def _run_scrape(mode: str) -> None:
    handler = _ProgressHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))

    loggers = [
        logging.getLogger(name) for name in (
            "kaitori_scraper.scrapers.fastbuy_scraper",
            "kaitori_scraper.scrapers.onechome_scraper",
        )
    ]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)

    try:
        items = get_collection_by_ids(None)
        _update(total_items=len(items))
        timestamp = datetime.now()
        fastbuy_results = []
        onechome_results = []

        if mode == "both":
            _update(phase="Scraping both sites in parallel...")
            fastbuy_results, onechome_results = await asyncio.gather(
                FastbuyScraper().scrape(items),
                OneChomeScraper().scrape(items),
            )
            _update(progress=0.95)
        elif mode == "fastbuy":
            _update(phase="Scraping fastbuy.jp...")
            fastbuy_results = await FastbuyScraper().scrape(items)
            _update(progress=0.9)
        elif mode == "onechome":
            _update(phase="Scraping 1-chome.com...")
            onechome_results = await OneChomeScraper().scrape(items)
            _update(progress=0.9)

        _update(phase="Comparing results...")
        comparison = compare_results(items, fastbuy_results, onechome_results)

        text_content = generate_text_report(comparison, timestamp)
        csv_content = generate_csv_report(comparison, timestamp)

        _update(
            status="completed",
            progress=1.0,
            phase="Complete",
            completed_at=datetime.now(),
            results=comparison,
            csv_content=csv_content,
            text_content=text_content,
        )

    except Exception as e:
        _update(
            status="error",
            phase=f"Error: {e}",
            error_message=str(e),
        )

    finally:
        for lg in loggers:
            lg.removeHandler(handler)


def start_scrape(mode: str) -> bool:
    """Start a background scrape. Returns False if already running."""
    state = get_state()
    if state.status == "running":
        return False

    global _state
    with _lock:
        _state = ScrapeState(
            status="running",
            mode=mode,
            phase="Initializing...",
            started_at=datetime.now(),
        )

    asyncio.run_coroutine_threadsafe(_run_scrape(mode), _loop)
    return True
