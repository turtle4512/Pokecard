from kaitori_scraper.models.data import (
    CollectionItem, MatchResult, ComparisonRow,
)


def compare_results(
    items: list[CollectionItem],
    fastbuy_results: list[MatchResult],
    onechome_results: list[MatchResult],
) -> list[ComparisonRow]:
    fb_by_id = {r.collection_item.id: r for r in fastbuy_results}
    oc_by_id = {r.collection_item.id: r for r in onechome_results}

    rows = []
    for item in items:
        fb = fb_by_id.get(item.id)
        oc = oc_by_id.get(item.id)

        row = ComparisonRow(
            collection_item=item,
            fastbuy_match=fb,
            onechome_match=oc,
        )

        fb_price = _midpoint(fb) if fb and fb.product else None
        oc_price = _midpoint(oc) if oc and oc.product else None

        if fb_price is not None and oc_price is not None:
            row.price_diff = oc_price - fb_price
            if row.price_diff > 0:
                row.recommendation = "1-chome"
            elif row.price_diff < 0:
                row.recommendation = "fastbuy"
            else:
                row.recommendation = "同じ"

        rows.append(row)

    return rows


def _midpoint(match: MatchResult) -> int | None:
    if not match or not match.product:
        return None
    p = match.product
    if p.price_high:
        return (p.price_low + p.price_high) // 2
    return p.price_low
