# ポケモンカード買取価格爬虫系统

**技術設計書 v4.0（実装完了版）**

対象サイト: fastbuy.jp × 買取一丁目 (1-chome.com)

---

## 1. 项目概述

本项目基于你的18种宝可梦卡牌收藏（未开封BOX/套装），通过模拟手动搜索的方式在 fastbuy.jp 和買取一丁目(1-chome.com) 两个日本买取店网站上查询买取价格，并生成对比报告。所有搜索关键词优先使用日语原文。

### 1.1 收藏品覆盖范围

| # | 商品名 | 系列号 | 数量 | 类型 | 主搜索关键词（日語） |
|---|--------|--------|------|------|----------------------|
| 1 | 変幻の仮面 BOX | sv6 | 1 | BOX | 変幻の仮面 |
| 2 | クリムゾンヘイズ BOX | sv5a | 1 | BOX | クリムゾンヘイズ |
| 3 | サイバージャッジ BOX | sv5M | 1 | BOX | サイバージャッジ |
| 4 | ワイルドフォース BOX | sv5K | 1 | BOX | ワイルドフォース |
| 5 | シャイニートレジャーex BOX | sv4a | 2 | BOX | シャイニートレジャーex |
| 6 | 未来の一閃 BOX | sv4M | 1 | BOX | 未来の一閃 |
| 7 | 黒炎の支配者 BOX | sv3 | 2 | BOX | 黒炎の支配者 |
| 8 | クレイバースト BOX | sv2D | 2 | BOX | クレイバースト |
| 9 | バイオレットex BOX | sv1V | 1 | BOX | バイオレットex |
| 10 | VSTARユニバース BOX | s12a | 6 | BOX | VSTARユニバース |
| 11 | パラダイムトリガー BOX | s12 | 2 | BOX | パラダイムトリガー |
| 12 | タイムゲイザー BOX | s10D | 1 | BOX | タイムゲイザー |
| 13 | Pokémon GO スペシャルセット | s10b | 1 | セット | Pokémon GO スペシャル |
| 14 | ポケモンカード151 BOX | sv2a | 3 | BOX | ポケモンカード151 |
| 15 | 151 カードファイルセット | sv2a | 2 | セット | 151 カードファイル |
| 16 | ポケモンカードゲーム Classic | CL | 1 | セット | ポケモン Classic |
| 17 | スノーハザード＆クレイバースト ジムセット | sv2 | 1 | セット | ジムセット ナンジャモ |
| 18 | スターターセットex ピカチュウ | svC | 1 | セット | スターターセットex ピカチュウ |

---

## 2. 站点实测分析结果

### 2.1 fastbuy.jp — 实测确认

**渲染方式:** 服务端渲染 (SSR)。HTTP GET 请求直接返回完整 HTML，包含全部商品名称、价格、链接。

**已验证 URL 规则:**

```
# 分类浏览（第1页）— 已测试成功
https://fastbuy.jp/index/index/categorydetail?id=8

# 翻页 — 已确认格式（共7页）
https://fastbuy.jp/index/index/categorydetail?hide_next=1&id=8&page={2-7}

# 商品详情
https://fastbuy.jp/index.php/index/index/goodsdetail?id={product_id}

# 已确认的分类 ID:
#   ポケモン = 8 | 遊戯王 = 16 | ONE PIECE = 17 | フィギュア = 18
#   Labubu = 30 | 拡張パック = 36 | 買取強化商品 = -1
```

**页面结构实测 (第1页样本):**

| 实测发现 | HTML 特征 | 提取策略 |
|----------|-----------|----------|
| 商品卡片 | `a[href*='goodsdetail']` 包裹整个卡片 | 选择所有含 goodsdetail 的链接 |
| 商品名称 | 图片后的长文本节点 | 过滤掉短文本(強化/色选择)后取第一个长文本 |
| 价格格式 | 两种: `¥X,XXX` 或 `X,XXX ~ Y,YYY円` | 正则: 4组交替匹配（¥前缀 OR 円后缀），见下方 |
| 买取强化标记 | 文本中包含「強化」 | 检查卡片文本中是否含「強」 |
| 颜色变体 | 黒/金/白/灰 四种选择 | 区间价对应不同颜色变体 |
| 分页控件 | `a[href*='page=N']` 链接 | 检查是否存在 page=N+1 链接 |
| 每页商品数 | 约12个 | 7页 ≈ 76个商品（实测） |

**价格正则（实装版）:**

商品名中含有裸数字（如「151」）会导致误匹配，因此正则必须要求 `¥/￥` 前缀 **或** `円` 后缀：

```python
# 4组交替: (¥low, ¥high) | (円low, 円high)
FASTBUY_PRICE_PATTERN = r"(?:[￥¥]\s*(\d{1,3}(?:,\d{3})*)\s*(?:[~～]\s*(\d{1,3}(?:,\d{3})*))?|(\d{1,3}(?:,\d{3})*)\s*(?:[~～]\s*(\d{1,3}(?:,\d{3})*))?\s*円)"
```

**实测第1页商品样本（与你的收藏相关的商品）:**

| 商品名（网站原文） | 价格 | 状态 |
|--------------------|------|------|
| ポケモンカードゲーム MEGA 拡張パック ムニキスゼロ BOX | ¥5,900 ~ 6,800 | 買取強化 |
| MEGAドリームex BOX | ¥7,500 ~ 9,500 | 買取強化 |
| ポケモンカードゲーム スカーレット&バイオレット拡張パック 「ロケット団の栄光」 | ¥15,000 | 買取強化 |
| ポケモンカードゲーム スカーレット＆バイオレット 拡張パック 「ホワイトフレア」 | ¥9,500 ~ 12,000 | 買取強化 |
| ポケモンカードゲーム スカーレット＆バイオレット 拡張パック 「ブラックボルト」 | ¥11,000 ~ 13,500 | 買取強化 |

> **注意:** 第1页主要是MEGA/SV最新系列。你的收藏中较早的系列（sv2D, sv3, s12a等）预计在第3-7页。爬虫需要遍历全部7页才能覆盖完整。

### 2.2 1-chome.com — 实测确认（含截图分析）

> **关键发现:** 1-chome.com 确实有宝可梦卡牌 BOX 买取。使用关键词「ポケモン」搜索后，出现了ポケモンカード相关商品。无需登录即可搜索和查看价格。

**渲染方式:** SPA 单页应用（**Element Plus / Vue.js** 框架，Playwright DOM 检查で確認済み）。HTTP 直接请求只返回空壳 HTML，全部商品数据通过 JavaScript 异步加载，必须通过 Playwright 浏览器自动化获取。

**登录要求:** 不需要登录。直接搜索关键词即可出现卡牌 BOX 的商品和价格信息。爬虫无需处理认证逻辑。

**截图分析 — 搜索结果页结构:**

| 分析项 | 从截图中确认的信息 |
|--------|-------------------|
| 搜索关键词 | 「ポケモン」— 宽泛搜索即可命中卡牌 BOX 商品 |
| 商品卡片布局 | 2列网格布局，每个卡片包含: 图片 + 商品名 + JAN码 + 状态 + 价格 + 购物车 |
| 商品名格式 | 【系列前缀】+ 商品名 + 类型。如「【S&V】ロケット団の栄光 BOX」 |
| 系列前缀 | 使用方括号标注: 【S&V】= スカーレット＆バイオレット / 【NS1】等 |
| JAN 码 | 每件商品有 JAN 条码（如 4902370551563），可用于精确匹配 |
| 价格格式 | 「新品  ¥X,XXX」— 价格与状态（新品）在同一行 |
| 价格类型 | 这是买取价格（网站收购价，即你卖给店铺的价格） |
| 购物车功能 | 有数量选择器和「カートに入れる」按钮 |
| 登录状态 | 需要登录（截图显示 WU...様 已登录） |
| 已确认的卡牌商品 | ロケット団の栄光 BOX / 熱風のアリーナ BOX / ポケなで モンスターボール 等 |

**已采用方案: Playwright 直接搜索**

实测 18 件商品搜索耗时约 2.5 分钟（含 3-6 秒随机间隔）。

### 2.3 双站点实测对比总结

| 对比项 | fastbuy.jp | 1-chome.com |
|--------|------------|-------------|
| 渲染方式 | SSR — HTML含完整数据 | SPA — Element Plus / Vue.js |
| 爬取方案 | httpx + BeautifulSoup | Playwright 浏览器自动化 |
| 搜索机制 | 分类浏览(id=8) + 翻页 7页 | 逐关键词搜索 |
| 商品名格式 | 完整日文名（长名称） | 【系列】简称 BOX |
| 价格格式 | `¥X,XXX` 或 `X,XXX~Y,YYY円` | `¥X,XXX`（单一买取价） |
| 登录要求 | 不需要 | 不需要 |
| JAN码 | 无 | 有（13桁、テキスト中に `JAN: XXXXXXXXXXXXX`） |
| 实测耗时 | ~22 秒（7页爬取） | ~2.5 分钟（18件搜索） |
| 搜索语言 | 日本語（商品原名） | 日本語 |

---

## 3. 核心搜索与匹配策略

### 3.1 日语优先搜索策略

两个网站都是日本站点，商品名全部为日语。搜索关键词必须使用日语原文，否则无法匹配。

**关键词设计原则:**

- **第1关键词:** 日文商品名中最核心的短语（如「クレイバースト」而非完整商品名）
- **第2关键词:** 日文完整名 + BOX（如「クレイバースト BOX」）
- **第3关键词:** 系列号（如「sv2D BOX」）
- 每件商品配置 2-4 组关键词，按精确度从高到低排列

**特殊商品的关键词策略:**

| 商品 | 关键词设计说明 |
|------|---------------|
| 151 カードファイルセット | 搜索「151 カードファイル」而非具体版本名，覆盖妙蛙/喷火/水箭/精灵球全部版本 |
| ポケモンカードゲーム Classic | 搜索「ポケモン Classic」或「カードゲーム Classic」 |
| ジムセット（ナンジャモ） | 搜索「ジムセット ナンジャモ」或「スノーハザード クレイバースト ジムセット」 |
| Pokémon GO スペシャルセット | 搜索「Pokémon GO スペシャル」和「ポケモン GO スペシャル」两种写法 |

### 3.2 fastbuy.jp 搜索策略

**推荐方案: 全量爬取 + 本地模糊匹配**

不使用站内搜索框，而是直接爬取ポケモン分类的全部7页商品（约84个），在本地建立完整商品索引，然后用模糊匹配算法为每件收藏找到最佳对应商品。

**优势:**

- 只需发送7次HTTP请求即可覆盖全部商品
- 避免站内搜索的不确定性（搜索框行为未经验证）
- 支持灵活的模糊匹配，可以匹配到部分名称命中的商品
- 一次爬取，18件收藏同时匹配

**流程:**

```
Step 1: GET /index/index/categorydetail?id=8  →  解析第1页
    ↓
Step 2: 循环 page=2..7，爬取全部后续页
    ↓
Step 3: 建立商品索引: {名称, 价格, URL, 是否强化} × ~84个
    ↓
Step 4: 对每件收藏，用多组日语关键词进行模糊匹配
    ↓
Step 5: 取匹配度最高的结果，记录价格
```

### 3.3 1-chome.com 搜索策略

**推荐方案: Playwright 逐关键词搜索**

根据截图确认，1-chome 搜索「ポケモン」可以出现卡牌BOX。商品名使用【系列】前缀格式，每个商品有 JAN 码。搜索关键词可以用商品名的核心部分（日语）。

**搜索关键词策略（基于截图商品名格式调整）:**

1-chome 商品名格式为「【S&V】ロケット団の栄光 BOX」，其中核心部分是「ロケット団の栄光」。搜索时不需要加系列前缀和BOX后缀，直接搜索日文核心名即可。

| # | 你的商品 | 1-chome搜索关键词 | 预期匹配 |
|---|---------|-------------------|---------|
| 1 | 変幻の仮面 BOX | 変幻の仮面 | 【S&V】変幻の仮面 BOX |
| 5 | シャイニートレジャーex BOX | シャイニートレジャー | 【S&V】シャイニートレジャーex BOX |
| 8 | クレイバースト BOX | クレイバースト | 【S&V】クレイバースト BOX |
| 10 | VSTARユニバース BOX | VSTARユニバース | 【S&S】VSTARユニバース BOX |
| 14 | ポケモンカード151 BOX | 151 | 【S&V】ポケモンカード151 BOX |
| 16 | ポケモンカードゲーム Classic | Classic | ポケモンカードゲーム Classic |

**流程:**

```
Step 1: Playwright 启动 → 导航到 1-chome.com（无需登录）
    ↓
Step 2: 定位搜索框，输入日語关键词（如「クレイバースト」）
    ↓
Step 3: 提交搜索，等待 /searchResult 页面渲染
    ↓
Step 4: 解析商品卡片: 提取【系列】商品名、JAN码、新品/中古状态、¥价格
    ↓
Step 5: 用模糊匹配找到最佳对应商品（优先匹配 JAN 码或商品名核心部分）
    ↓
Step 6: 若未命中，尝试下一组关键词（最多3组）
    ↓
Step 7: 搜索间隔 3-6秒，18件商品约需 5-10 分钟
```

**DOM 选择器（Playwright 実機確認済み）:**

```python
# Element Plus / Vue.js — 已通过 Playwright DOM 检查确认
ONECHOME_SELECTORS = {
    "search_input": "input.el-input__inner[placeholder*='商品名']",
    "search_button": "button.search-btn",
    "product_card": ".commodity-item",
    "product_name": ".commodity-content .title",
}
```

**商品卡片 inner_text 结构（実測）:**

```
【S＆V】クレイバースト BOX        ← 商品名（第一行含【前缀】）
JAN: 4521329346182               ← JAN码（13桁）
ポケモンカード                    ← 分类
※シュリンク付き、新品未開封        ← 备注
新品                              ← 状态
¥11,000                          ← 买取价格
カートに入れる                    ← 按钮文本
```

**价格正则:**

```python
ONECHOME_PRICE_PATTERN = r"[￥¥]\s*(\d{1,3}(?:,\d{3})*)"
```

### 3.4 模糊匹配算法

由于网站上的商品名通常比搜索关键词长（如完整名「ポケモンカードゲーム ソード＆シールド ハイクラスパック VSTARユニバース」vs 搜索词「VSTARユニバース」），采用多级匹配策略：

1. **子串包含检查:** 关键词是否完整出现在商品名中 → 分数 0.95
2. **反向包含检查:** 商品名是否完整出现在关键词中 → 分数 0.90
3. **SequenceMatcher 序列相似度** → 分数 0-1
4. **关键词命中率:** 将两者分词后计算交集比例 → 分数 0-1（**含 stopword 过滤**）
5. 取以上最高分作为最终匹配度，阈值设为 **0.5**

**正规化处理:** 比較前に lowercase、全角→半角（＆→&, ～→~）、空白圧縮を実施。

**Stopword 过滤（Level 4 分词匹配时使用）:**

「BOX」「ボックス」「パック」「セット」「拡張」「強化」「ポケモンカードゲーム」「ポケモンカード」「ポケモン」「スカーレット」「バイオレット」「ソード」「シールド」「拡張パック」「ハイクラスパック」「強化拡張パック」「ex」「mega」

> **実装時の教訓:** Stopword 未導入時、「タイムゲイザー BOX」が「BOX」トークン一致だけで全く別の商品にスコア 0.50 で誤マッチしていた。Stopword フィルタリング追加で解消。

---

## 4. 数据模型

> **実装注記:** 初版は SQLite を使わず、Python dataclass でインメモリ処理。将来の価格履歴追跡に向けて SQLite 追加を検討中。

### 4.1 核心数据类 (`models/data.py`)

```python
class ProductType(Enum):
    BOX = "BOX"
    SET = "SET"

class Site(Enum):
    FASTBUY = "fastbuy"
    ONECHOME = "1chome"

@dataclass
class CollectionItem:
    id: int                          # 收藏编号 1-18
    name_jp: str                     # 日語商品名
    series: str                      # 系列号 (sv6, s12a 等)
    quantity: int                    # 持有数量
    product_type: ProductType        # BOX / SET
    search_keywords: list[str]       # 日語搜索关键词（2-4组，按精确度排序）

@dataclass
class ScrapedProduct:
    site: Site                       # 来源站点
    name: str                        # 商品名（网站原文）
    price_low: int                   # 买取价下限（日元）
    price_high: int | None = None    # 买取价上限（区间价时）
    product_url: str | None = None   # 商品详情页 URL
    product_id: str | None = None    # 站内商品 ID
    jan_code: str | None = None      # JAN 条码（1-chome 专用）
    is_enhanced: bool = False        # 買取強化フラグ（fastbuy 专用）
    variant: str | None = None       # 颜色变体
    condition: str | None = None     # 新品 / 中古

@dataclass
class MatchResult:
    collection_item: CollectionItem  # 对应的收藏品
    product: ScrapedProduct | None   # 匹配到的商品（None=未匹配）
    score: float                     # 匹配度 0.0-1.0
    matched_keyword: str | None      # 命中的搜索关键词
    site: Site                       # 来源站点

@dataclass
class ComparisonRow:
    item: CollectionItem             # 收藏品
    fastbuy_match: MatchResult | None
    onechome_match: MatchResult | None
    price_diff: int | None           # 价格差（正=1-chome高）
    recommendation: str | None       # "fastbuy" / "1-chome" / "同じ"
```

---

## 5. 项目结构与技术栈

> **設計書からの変更点:**
> - `parsers/` を `scrapers/` に統合（各 parser は 1 つの scraper 専用のため分離不要）
> - YAML 設定 → Python 定数（`config/settings.py`）に変更。pyyaml 依存を排除
> - `notifier.py` は初版スキップ（P5 機能）
> - `models/data.py` を新設（共有データクラス）
> - SQLite 延期 → インメモリ処理 + レポート出力

```
kaitori_scraper/                  # パッケージルート
├── __init__.py
├── __main__.py                   # python -m kaitori_scraper 対応
├── main.py                       # CLI 入口 (argparse + asyncio)
├── config/
│   ├── __init__.py
│   ├── collection.py             # 18件收藏清单 + 日語搜索关键词
│   └── settings.py               # URL/选择器/UA池/延迟/正则 全配置
├── models/
│   ├── __init__.py
│   └── data.py                   # 共享 dataclass (CollectionItem, ScrapedProduct 等)
├── scrapers/
│   ├── __init__.py
│   ├── base.py                   # BaseScraper ABC (延迟/重试/UA)
│   ├── fastbuy_scraper.py        # SSR爬虫: httpx + BeautifulSoup（含解析）
│   └── onechome_scraper.py       # SPA爬虫: Playwright（含解析）
├── matcher/
│   ├── __init__.py
│   └── fuzzy_match.py            # 4级模糊匹配 + stopword 过滤
└── output/
    ├── __init__.py
    ├── comparator.py             # 双站中间价对比
    └── report.py                 # 文本报告 + CSV (utf-8-sig)
requirements.txt                  # httpx, beautifulsoup4, lxml, playwright
```

**运行命令:**

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 完整模式（两个站点）
python -m kaitori_scraper.main

# 仅 fastbuy（无需 Playwright）
python -m kaitori_scraper.main --fastbuy-only

# 仅 1-chome
python -m kaitori_scraper.main --onechome-only

# 指定收藏编号 + 详细日志
python -m kaitori_scraper.main --items 5,8,14 -v

# Windows 环境推荐（确保 UTF-8 输出）
python -X utf8 -m kaitori_scraper.main
```

> **Windows 注意:** 默认使用 `ProactorEventLoop`（Playwright subprocess 需要）。不可设置 `WindowsSelectorEventLoopPolicy`。

---

## 6. 反爬对抗策略

两站均为中小型买取店网站，反爬机制宽松，但仍需基本伪装：

| 策略 | 实现 |
|------|------|
| User-Agent | Chrome/Firefox/Safari 多版本UA池，每次请求随机选择 |
| Accept-Language | 固定 `ja,en-US;q=0.9` — 模拟日本用户 |
| Referer 链 | fastbuy: 首页→分类页→翻页 / 1-chome: 首页→搜索结果 |
| 请求延迟 | fastbuy 翻页: 2-4秒 / 1-chome 搜索间: 3-6秒 |
| 异常处理 | 指数退避（base=2秒），最大重试3次 |
| 代理 | 初期不需要。若IP被封，可接入自建代理 |

---

## 7. 输出报告格式

爬虫执行完成后生成两种格式的报告（文件名含时间戳 `price_report_YYYYMMDD_HHMMSS`）：

### 7.1 文本报告 (price_report_*.txt)

```
==================================================
  ポケモンカード 買取価格レポート
  查询时间: 2026-02-20 01:16:14
==================================================

--- [8] クレイバースト BOX (sv2D) x 2 ---

  fastbuy.jp:  ¥8,000 ~ ¥11,300
    匹配商品: ポケモンカードゲーム ...「クレイバースト」ボックス
    匹配度: 100%  |  链接: https://fastbuy.jp/...

  1-chome:     ¥11,000
    匹配商品: 【S＆V】クレイバースト BOX
    匹配度: 100%

  対比: 1-chome 高 ¥1,350

==================================================
  汇总（含数量）
  fastbuy 合计: ¥XXX,XXX ~ ¥XXX,XXX
  1-chome 合计: ¥XXX,XXX
==================================================
```

### 7.2 CSV 报告 (price_report_*.csv)

使用 `utf-8-sig` 编码（BOM）确保 Excel 正确打开日文。包含字段: 编号、商品名、系列、数量、fastbuy 价格(上下限)、fastbuy 匹配商品、fastbuy 匹配度、1-chome 价格(上下限)、1-chome 匹配商品、1-chome 匹配度、价格差异、推荐站点。

---

## 8. 开发计划

| 阶段 | 任务 | 状态 |
|------|------|------|
| P1 | fastbuy 全量爬取 + 18件匹配 | ✅ 完成 — 76 商品爬取、17/18 匹配成功 |
| P2 | 1-chome Playwright DOM 分析 | ✅ 完成 — Element Plus/Vue.js 确认 |
| P3 | 1-chome 爬虫开发 | ✅ 完成 — 11/18 匹配成功 |
| P4 | 双站对比 + 报告生成 | ✅ 完成 — 文本 + CSV 报告 |
| P5 | 定时任务 + 告警 | 未着手 |

---

## 9. 已知问题与改善余地

**匹配结果:**

| 商品 | fastbuy | 1-chome | 备注 |
|------|---------|---------|------|
| #1-10 (主流 BOX) | ✅ 100% | ✅ 100% | 完璧マッチ |
| #11 パラダイムトリガー | ✅ 100% | ❌ | 1-chome 在庫なし |
| #12 タイムゲイザー | ❌ | ❌ | 両站とも在庫なし |
| #13 Pokémon GO セット | ⚠️ 50% | ❌ | fastbuy 误匹配到 GO ボックス |
| #14 ポケモンカード151 | ✅ 100% | ✅ 100% | |
| #15 カードファイルセット | ⚠️ 50% | ❌ | fastbuy 误匹配到 151 BOX |
| #16 Classic | ⚠️ 51% | ❌ | fastbuy 误匹配到 MEGA 拡張パック |
| #17 ジムセット | ⚠️ 50% | ❌ | 名称に近いが完全一致ではない |
| #18 スターターセット | ⚠️ 50% | ❌ | fastbuy 误匹配到 WCS ピカチュウ |

**潜在改善:**

- 提高匹配阈值或为低置信度匹配添加警告标记
- 为 #13, #15-18 等特殊商品添加更精确的搜索关键词
- 考虑 JAN 码精确匹配（1-chome 有 JAN 数据）
- SQLite 持久化，实现价格推移追跡
- 定时执行 + 价格变动通知（P5）

---

| 文档版本 | v4.0（実装完了版） |
|---------|----------------------|
| 更新日期 | 2026-02-20 |
| 目标站点 | fastbuy.jp / 1-chome.com |
| 收藏品数量 | 18种 / 共约35件 |
| 搜索语言 | 日本語優先 |
| 技術栈 | Python 3.12 / httpx / BeautifulSoup / Playwright / asyncio |
