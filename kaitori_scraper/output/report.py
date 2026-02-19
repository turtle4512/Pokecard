import csv
import io
from datetime import datetime
from pathlib import Path

from kaitori_scraper.models.data import ComparisonRow, MatchResult


def generate_text_report(rows: list[ComparisonRow], timestamp: datetime) -> str:
    lines = []
    lines.append("=" * 50)
    lines.append("  ポケモンカード 買取価格レポート")
    lines.append(f"  查询时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 50)
    lines.append("")

    total_fb_low = 0
    total_fb_high = 0
    total_oc = 0
    has_fb = False
    has_oc = False

    for row in rows:
        item = row.collection_item
        lines.append(
            f"--- [{item.id}] {item.name_jp} ({item.series}) x {item.quantity} ---"
        )
        lines.append("")

        # fastbuy
        if row.fastbuy_match and row.fastbuy_match.product:
            p = row.fastbuy_match.product
            has_fb = True
            enhanced = " 🔥買取強化" if p.is_enhanced else ""
            if p.price_high:
                price_str = f"¥{p.price_low:,} ~ ¥{p.price_high:,}"
                total_fb_low += p.price_low * item.quantity
                total_fb_high += p.price_high * item.quantity
            else:
                price_str = f"¥{p.price_low:,}"
                total_fb_low += p.price_low * item.quantity
                total_fb_high += p.price_low * item.quantity
            lines.append(f"  fastbuy.jp:  {price_str}{enhanced}")
            lines.append(f"    匹配商品: {p.name}")
            lines.append(
                f"    匹配度: {row.fastbuy_match.score:.0%}  |  "
                f"链接: {p.product_url or 'N/A'}"
            )
        else:
            lines.append("  fastbuy.jp:  未找到匹配商品")

        lines.append("")

        # 1-chome
        if row.onechome_match and row.onechome_match.product:
            p = row.onechome_match.product
            has_oc = True
            price_str = f"¥{p.price_low:,}"
            total_oc += p.price_low * item.quantity
            lines.append(f"  1-chome:     {price_str}")
            lines.append(f"    匹配商品: {p.name}")
            lines.append(f"    匹配度: {row.onechome_match.score:.0%}")
        else:
            lines.append("  1-chome:     未找到匹配商品")

        lines.append("")

        # comparison
        if row.price_diff is not None:
            if row.price_diff > 0:
                lines.append(f"  対比: 1-chome 高 ¥{row.price_diff:,}")
            elif row.price_diff < 0:
                lines.append(f"  対比: fastbuy 高 ¥{abs(row.price_diff):,}")
            else:
                lines.append("  対比: 同じ価格")

        lines.append("")

    # summary
    lines.append("=" * 50)
    lines.append("  汇总（含数量）")
    if has_fb:
        if total_fb_low == total_fb_high:
            lines.append(f"  fastbuy 合计: ¥{total_fb_low:,}")
        else:
            lines.append(f"  fastbuy 合计: ¥{total_fb_low:,} ~ ¥{total_fb_high:,}")
    if has_oc:
        lines.append(f"  1-chome 合计: ¥{total_oc:,}")
    lines.append("=" * 50)

    return "\n".join(lines)


def generate_csv_report(rows: list[ComparisonRow], timestamp: datetime) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "編号", "商品名(日)", "系列", "数量",
        "fastbuy下限", "fastbuy上限", "fastbuy匹配商品", "fastbuy匹配度",
        "1chome価格", "1chome匹配商品", "1chome匹配度",
        "価格差(1chome-fastbuy)", "推奨",
    ])

    for row in rows:
        item = row.collection_item
        fb = row.fastbuy_match
        oc = row.onechome_match

        writer.writerow([
            item.id,
            item.name_jp,
            item.series,
            item.quantity,
            fb.product.price_low if fb and fb.product else "",
            fb.product.price_high or fb.product.price_low if fb and fb.product else "",
            fb.product.name if fb and fb.product else "",
            f"{fb.score:.0%}" if fb and fb.product else "",
            oc.product.price_low if oc and oc.product else "",
            oc.product.name if oc and oc.product else "",
            f"{oc.score:.0%}" if oc and oc.product else "",
            row.price_diff if row.price_diff is not None else "",
            row.recommendation or "",
        ])

    return output.getvalue()


def save_reports(
    rows: list[ComparisonRow],
    output_dir: str = ".",
    timestamp: datetime | None = None,
) -> tuple[str, str]:
    if timestamp is None:
        timestamp = datetime.now()

    date_str = timestamp.strftime("%Y%m%d_%H%M%S")

    text_content = generate_text_report(rows, timestamp)
    text_path = Path(output_dir) / f"price_report_{date_str}.txt"
    text_path.write_text(text_content, encoding="utf-8")

    csv_content = generate_csv_report(rows, timestamp)
    csv_path = Path(output_dir) / f"price_report_{date_str}.csv"
    csv_path.write_text(csv_content, encoding="utf-8-sig")  # BOM for Excel

    return str(text_path), str(csv_path)
