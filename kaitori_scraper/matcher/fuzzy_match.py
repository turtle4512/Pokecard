"""
Multi-level fuzzy matching for Japanese product names.

Levels (take max score):
1. Substring containment: keyword in product name -> 0.95
2. Reverse containment: product name in keyword -> 0.90
3. SequenceMatcher similarity -> 0.0-1.0
4. Keyword hit rate: tokenized intersection -> 0.0-1.0
"""

import re
from difflib import SequenceMatcher

from kaitori_scraper.models.data import (
    CollectionItem, ScrapedProduct, MatchResult, Site,
)
from kaitori_scraper.config.settings import MATCH_THRESHOLD


def _normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("＆", "&").replace("～", "~")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Generic terms that appear in many product names and cause false matches
_STOP_WORDS = {
    "box", "ボックス", "パック", "セット", "拡張", "強化", "ポケモンカードゲーム",
    "ポケモンカード", "ポケモン", "スカーレット", "バイオレット", "ソード", "シールド",
    "拡張パック", "ハイクラスパック", "強化拡張パック", "ex", "mega",
}


def _tokenize(text: str, filter_stopwords: bool = False) -> set[str]:
    cleaned = re.sub(r"[【】\[\]「」（）()・×/]", " ", text)
    tokens = set(cleaned.split())
    tokens = {t for t in tokens if len(t) > 1}
    if filter_stopwords:
        tokens = {t for t in tokens if t.lower() not in _STOP_WORDS}
    return tokens


def compute_match_score(keyword: str, product_name: str) -> float:
    kw = _normalize(keyword)
    pn = _normalize(product_name)

    scores = []

    # Level 1: keyword is substring of product name
    if kw in pn:
        scores.append(0.95)

    # Level 2: product name is substring of keyword
    if pn in kw:
        scores.append(0.90)

    # Level 3: SequenceMatcher
    scores.append(SequenceMatcher(None, kw, pn).ratio())

    # Level 4: token intersection (with stopword filtering)
    kw_tokens = _tokenize(keyword, filter_stopwords=True)
    pn_tokens = _tokenize(product_name, filter_stopwords=True)
    if kw_tokens:
        hit_rate = len(kw_tokens & pn_tokens) / len(kw_tokens)
        scores.append(hit_rate)

    return max(scores) if scores else 0.0


def find_best_match(
    item: CollectionItem,
    products: list[ScrapedProduct],
    site: Site,
) -> MatchResult:
    best_score = 0.0
    best_product = None
    best_keyword = None

    for keyword in item.search_keywords:
        for product in products:
            score = compute_match_score(keyword, product.name)
            if score > best_score:
                best_score = score
                best_product = product
                best_keyword = keyword

    if best_score < MATCH_THRESHOLD:
        return MatchResult(
            collection_item=item,
            product=None,
            score=best_score,
            matched_keyword=best_keyword,
            site=site,
        )

    return MatchResult(
        collection_item=item,
        product=best_product,
        score=best_score,
        matched_keyword=best_keyword,
        site=site,
    )
