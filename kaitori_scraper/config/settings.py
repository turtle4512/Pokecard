import random

# ── Fastbuy.jp ──

FASTBUY_BASE_URL = "https://fastbuy.jp/index/index/categorydetail"
FASTBUY_CATEGORY_ID = 8
FASTBUY_TOTAL_PAGES = 7
FASTBUY_REQUEST_DELAY = (0.5, 1.0)

FASTBUY_SELECTORS = {
    "product_card": "a[href*='goodsdetail']",
}

# Actual format from HTML: "5,900 ~ 7,000円" (no ¥ prefix, 円 suffix)
# Require 円 at end OR ¥ at start to avoid matching bare numbers in product names
FASTBUY_PRICE_PATTERN = r"(?:[￥¥]\s*(\d{1,3}(?:,\d{3})*)\s*(?:[~～]\s*(\d{1,3}(?:,\d{3})*))?|(\d{1,3}(?:,\d{3})*)\s*(?:[~～]\s*(\d{1,3}(?:,\d{3})*))?\s*円)"


def fastbuy_page_url(page: int) -> str:
    if page == 1:
        return f"{FASTBUY_BASE_URL}?id={FASTBUY_CATEGORY_ID}"
    return f"{FASTBUY_BASE_URL}?hide_next=1&id={FASTBUY_CATEGORY_ID}&page={page}"


# ── 1-chome.com ──

ONECHOME_BASE_URL = "https://1-chome.com"
ONECHOME_SEARCH_DELAY = (0.5, 1.0)
ONECHOME_SEARCH_TIMEOUT = 10000
ONECHOME_CONCURRENT_TABS = 6
ONECHOME_PRICE_PATTERN = r"[￥¥]\s*(\d{1,3}(?:,\d{3})*)"

# Confirmed via Playwright DOM inspection (Element Plus / Vue.js)
ONECHOME_SELECTORS = {
    "search_input": "input.el-input__inner[placeholder*='商品名']",
    "search_button": "button.search-btn",
    "product_card": ".commodity-item",
    "product_name": ".commodity-content .title",
}

# ── Anti-scraping ──

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS = {
    "Accept-Language": "ja,en-US;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def random_user_agent() -> str:
    return random.choice(USER_AGENTS)


# ── Matching ──

MATCH_THRESHOLD = 0.5

# ── Retry ──

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
