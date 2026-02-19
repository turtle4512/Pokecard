from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ProductType(Enum):
    BOX = "BOX"
    SET = "セット"


class Site(Enum):
    FASTBUY = "fastbuy"
    ONECHOME = "1chome"


@dataclass
class CollectionItem:
    """User's collection item (one of 18 products)."""
    id: int
    name_jp: str
    series: str
    quantity: int
    product_type: ProductType
    search_keywords: list[str]


@dataclass
class ScrapedProduct:
    """A product scraped from a site."""
    site: Site
    name: str
    price_low: int
    price_high: Optional[int] = None
    product_url: Optional[str] = None
    product_id: Optional[str] = None
    jan_code: Optional[str] = None
    is_enhanced: bool = False
    variant: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class MatchResult:
    """Result of matching a CollectionItem to a ScrapedProduct."""
    collection_item: CollectionItem
    product: Optional[ScrapedProduct]
    score: float
    matched_keyword: Optional[str]
    site: Site


@dataclass
class ComparisonRow:
    """One row in the final comparison report."""
    collection_item: CollectionItem
    fastbuy_match: Optional[MatchResult] = None
    onechome_match: Optional[MatchResult] = None
    price_diff: Optional[int] = None
    recommendation: Optional[str] = None
