from datetime import datetime, timedelta, timezone
import sqlite3


HISTORY_DAYS = 365


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
