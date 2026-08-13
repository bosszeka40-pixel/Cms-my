from datetime import datetime, timedelta, timezone
import sqlite3
import re
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


HISTORY_DAYS = 365
INTRADAY_HOURS = 30 * 24
NEWS_DAYS = 365
TIMEFRAME_MILLISECONDS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def ensure_table(database):
    with sqlite3.connect(database) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS market_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                pair TEXT NOT NULL,
                day TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                fetched_at TEXT NOT NULL,
                UNIQUE(exchange, pair, day)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_history_lookup "
            "ON market_history(exchange, pair, day)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS market_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL,
                pair TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                fetched_at TEXT NOT NULL,
                UNIQUE(exchange, pair, timeframe, timestamp)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_candles_lookup "
            "ON market_candles(exchange, pair, timeframe, timestamp)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS market_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                published_at INTEGER NOT NULL,
                fetched_at TEXT NOT NULL,
                UNIQUE(source, title, published_at)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_market_news_published "
            "ON market_news(published_at)"
        )


def store_candles(database, exchange_name, pair, candles):
    fetched_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as conn:
        conn.executemany(
            """INSERT INTO market_history
               (exchange, pair, day, open, high, low, close, volume, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(exchange, pair, day) DO UPDATE SET
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume,
                 fetched_at=excluded.fetched_at""",
            [
                (
                    exchange_name,
                    pair,
                    datetime.fromtimestamp(candle[0] / 1000, timezone.utc).date().isoformat(),
                    float(candle[1]),
                    float(candle[2]),
                    float(candle[3]),
                    float(candle[4]),
                    float(candle[5] or 0),
                    fetched_at,
                )
                for candle in candles
                if len(candle) >= 6 and candle[4] is not None
            ],
        )
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=HISTORY_DAYS - 1)).isoformat()
        conn.execute(
            "DELETE FROM market_history WHERE exchange = ? AND pair = ? AND day < ?",
            (exchange_name, pair, cutoff),
        )


def last_day(database, exchange_name, pair):
    with sqlite3.connect(database) as conn:
        row = conn.execute(
            "SELECT MAX(day) FROM market_history WHERE exchange = ? AND pair = ?",
            (exchange_name, pair),
        ).fetchone()
    return row[0] if row else None


def load_history(database, exchange_name, pair):
    with sqlite3.connect(database) as conn:
        rows = conn.execute(
            """SELECT day, open, high, low, close, volume
               FROM market_history
               WHERE exchange = ? AND pair = ?
               ORDER BY day ASC""",
            (exchange_name, pair),
        ).fetchall()
    return [
        {"day": row[0], "open": row[1], "high": row[2], "low": row[3],
         "close": row[4], "volume": row[5]}
        for row in rows
    ]


def store_intraday_candles(database, exchange_name, pair, candles, timeframe="1h"):
    if timeframe not in TIMEFRAME_MILLISECONDS:
        raise ValueError(f"Неподдерживаемый таймфрейм: {timeframe}")
    fetched_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(database) as conn:
        conn.executemany(
            """INSERT INTO market_candles
               (exchange, pair, timeframe, timestamp, open, high, low, close, volume, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(exchange, pair, timeframe, timestamp) DO UPDATE SET
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume, fetched_at=excluded.fetched_at""",
            [
                (exchange_name, pair, timeframe, int(candle[0]), float(candle[1]),
                 float(candle[2]), float(candle[3]), float(candle[4]),
                 float(candle[5] or 0), fetched_at)
                for candle in candles
                if len(candle) >= 6 and candle[4] is not None
            ],
        )
        cutoff = int((datetime.now(timezone.utc) - timedelta(hours=INTRADAY_HOURS)).timestamp() * 1000)
        conn.execute(
            "DELETE FROM market_candles WHERE exchange = ? AND pair = ? "
            "AND timeframe = ? AND timestamp < ?",
            (exchange_name, pair, timeframe, cutoff),
        )


def load_candles(database, exchange_name, pair, timeframe="1h", limit=720):
    ensure_table(database)
    with sqlite3.connect(database) as conn:
        rows = conn.execute(
            """SELECT timestamp, open, high, low, close, volume
               FROM market_candles
               WHERE exchange = ? AND pair = ? AND timeframe = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (exchange_name, pair, timeframe, limit),
        ).fetchall()
    return [
        {"timestamp": row[0], "open": row[1], "high": row[2], "low": row[3],
         "close": row[4], "volume": row[5]}
        for row in reversed(rows)
    ]


def refresh_candles(database, exchange, exchange_name, pair, timeframe="1h", limit=720):
    ensure_table(database)
    since = int((datetime.now(timezone.utc) - timedelta(hours=INTRADAY_HOURS)).timestamp() * 1000)
    candles = []
    cursor = since
    while cursor < int(datetime.now(timezone.utc).timestamp() * 1000):
        batch = exchange.fetch_ohlcv(pair, timeframe=timeframe, since=cursor, limit=1000)
        if not batch:
            break
        candles.extend(batch)
        interval_ms = TIMEFRAME_MILLISECONDS[timeframe]
        next_cursor = batch[-1][0] + interval_ms
        if next_cursor <= cursor or len(batch) < 1000:
            break
        cursor = next_cursor
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    interval_ms = TIMEFRAME_MILLISECONDS[timeframe]
    candles = [candle for candle in candles if candle[0] + interval_ms <= now_ms]
    store_intraday_candles(database, exchange_name, pair, candles, timeframe)
    return load_candles(database, exchange_name, pair, timeframe, limit)


def refresh_history(database, exchange, exchange_name, pair):
    ensure_table(database)
    since = int((datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).timestamp() * 1000)
    existing_last = last_day(database, exchange_name, pair)
    if existing_last:
        since = max(since, int(datetime.fromisoformat(existing_last).replace(
            tzinfo=timezone.utc
        ).timestamp() * 1000))
    candles = []
    cursor = since
    while cursor < int(datetime.now(timezone.utc).timestamp() * 1000):
        batch = exchange.fetch_ohlcv(pair, timeframe="1d", since=cursor, limit=1000)
        if not batch:
            break
        candles.extend(batch)
        next_cursor = batch[-1][0] + 86400000
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(batch) < 1000:
            break
    store_candles(database, exchange_name, pair, candles)
    return load_history(database, exchange_name, pair)


def store_news(database, items):
    """Store only published news; future-dated items are ignored."""
    ensure_table(database)
    now = datetime.now(timezone.utc)
    fetched_at = now.isoformat()
    rows = []
    for item in items:
        title = str(item.get("title", "")).strip()
        published_at = int(item.get("published_at", 0))
        if title and published_at <= int(now.timestamp() * 1000):
            rows.append((str(item.get("source", "unknown")), title,
                         item.get("url"), published_at, fetched_at))
    with sqlite3.connect(database) as conn:
        conn.executemany(
            """INSERT INTO market_news(source, title, url, published_at, fetched_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source, title, published_at) DO UPDATE SET
                 url=excluded.url, fetched_at=excluded.fetched_at""",
            rows,
        )
        cutoff = int((now - timedelta(days=NEWS_DAYS)).timestamp() * 1000)
        conn.execute("DELETE FROM market_news WHERE published_at < ?", (cutoff,))


def load_news(database, as_of=None, limit=100):
    ensure_table(database)
    as_of = int(as_of if as_of is not None else datetime.now(timezone.utc).timestamp() * 1000)
    with sqlite3.connect(database) as conn:
        rows = conn.execute(
            """SELECT source, title, url, published_at FROM market_news
               WHERE published_at <= ? ORDER BY published_at DESC LIMIT ?""",
            (as_of, max(1, min(int(limit), 1000))),
        ).fetchall()
    return [{"source": row[0], "title": row[1], "url": row[2], "published_at": row[3]}
            for row in rows]


def analyze_news_sentiment(news):
    positive = {"surge", "gain", "gains", "bullish", " роста", "рост", "прибыль", "одобр"}
    negative = {"crash", "drop", "loss", "bearish", "паден", "убыт", "запрет", "взлом"}
    score = 0
    for item in news:
        title = item["title"].lower()
        score += any(word in title for word in positive)
        score -= any(word in title for word in negative)
    return max(-1.0, min(1.0, score / max(1, len(news))))


def refresh_news(database, feed_url="https://www.coindesk.com/arc/outboundfeeds/rss/"):
    request = Request(feed_url, headers={"User-Agent": "CMS market news reader/1.0"})
    with urlopen(request, timeout=10) as response:
        root = ET.fromstring(response.read())
    items = []
    for entry in root.findall(".//item"):
        title = (entry.findtext("title") or "").strip()
        published = entry.findtext("pubDate") or ""
        try:
            published_at = int(parsedate_to_datetime(published).timestamp() * 1000)
        except (TypeError, ValueError, OverflowError):
            continue
        items.append({"source": "coindesk", "title": re.sub(r"\s+", " ", title),
                      "url": entry.findtext("link"), "published_at": published_at})
    store_news(database, items)
    return load_news(database)
