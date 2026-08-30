/*
 * ExchangeFeed — прямое чтение публичного API бирж из браузера (CORS-эндпоинты),
 * чтобы не нагружать CMS-сервер запросами терминала.
 *
 * Биржа сама отвечает на запросы цены/стакана/конвертации; наш сервер используется
 * только как источник справочника инструментов (редкий кэш) и для исполнения сделок
 * (fail-closed execution gateway). Любой сбой прямого доступа тихо откатывается
 * на серверный просчёт /api/terminal/preview.
 */
(function (global) {
  'use strict';

  const TIMEOUT_MS = 6000;

  async function get(url) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    try {
      const resp = await fetch(url, { signal: ctrl.signal, mode: 'cors', cache: 'no-store' });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return await resp.json();
    } finally {
      clearTimeout(timer);
    }
  }

  /* Конфигурация публичных REST-endpoint'ов бирж. symbol — нативный id инструмента.
   * parse возвращает { bid, ask, last } (null-поля допустимы). */
  const CONF = {
    binance: {
      ticker: (symbol) => [
        `https://api.binance.com/api/v3/ticker/bookTicker?symbol=${encodeURIComponent(symbol)}`,
        (j) => ({ bid: parseFloat(j.bidPrice), ask: parseFloat(j.askPrice), last: null })
      ],
      price: (symbol) => [
        `https://api.binance.com/api/v3/ticker/price?symbol=${encodeURIComponent(symbol)}`,
        (j) => parseFloat(j.price)
      ]
    },
    bybit: {
      ticker: (symbol) => [
        `https://api.bybit.com/v5/market/tickers?category=spot&symbol=${encodeURIComponent(symbol)}`,
        (j) => {
          const r = (j.result && j.result.list && j.result.list[0]) || {};
          return { bid: parseFloat(r.bid1Price), ask: parseFloat(r.ask1Price), last: parseFloat(r.lastPrice) };
        }
      ],
      price: (symbol) => [
        `https://api.bybit.com/v5/market/tickers?category=spot&symbol=${encodeURIComponent(symbol)}`,
        (j) => {
          const r = (j.result && j.result.list && j.result.list[0]) || {};
          return parseFloat(r.lastPrice);
        }
      ]
    },
    okx: {
      ticker: (symbol) => [
        `https://www.okx.com/api/v5/market/ticker?instId=${encodeURIComponent(symbol)}`,
        (j) => {
          const r = (j.data && j.data[0]) || {};
          return { bid: parseFloat(r.bidPx), ask: parseFloat(r.askPx), last: parseFloat(r.last) };
        }
      ],
      price: (symbol) => [
        `https://www.okx.com/api/v5/market/ticker?instId=${encodeURIComponent(symbol)}`,
        (j) => {
          const r = (j.data && j.data[0]) || {};
          return parseFloat(r.last);
        }
      ]
    },
    bitfinex: {
      // Публичное тикер: [BID, BID_SIZE, ASK, ASK_SIZE, CHANGE, CHANGE_PCT, LAST, VOL, ...]
      ticker: (symbol) => [
        `https://api-pub.bitfinex.com/v2/ticker/${encodeURIComponent(symbol)}`,
        (j) => ({ bid: Number(j[0]), ask: Number(j[2]), last: Number(j[6]) })
      ],
      price: (symbol) => [
        `https://api-pub.bitfinex.com/v2/ticker/${encodeURIComponent(symbol)}`,
        (j) => Number(j[6])
      ]
    },
    pionex: {
      ticker: (symbol) => [
        `https://api.pionex.com/api/v1/market/tickers?symbol=${encodeURIComponent(symbol)}`,
        (j) => {
          const t = ((j.data || {}).tickers || []).find((x) => String(x.symbol) === String(symbol)) || {};
          const last = parseFloat(t.close) || parseFloat(t.last);
          return { bid: last, ask: last, last };
        }
      ],
      price: (symbol) => [
        `https://api.pionex.com/api/v1/market/tickers?symbol=${encodeURIComponent(symbol)}`,
        (j) => {
          const t = ((j.data || {}).tickers || []).find((x) => String(x.symbol) === String(symbol)) || {};
          return parseFloat(t.close) || parseFloat(t.last);
        }
      ]
    }
  };

  async function _quote(exchange, symbol, kind) {
    const cfg = CONF[exchange];
    if (!symbol || !cfg || !cfg[kind]) throw new Error(exchange + ' direct недоступен');
    const [url, parse] = cfg[kind](symbol);
    return parse(await get(url));
  }

  function directTicker(exchange, symbol) {
    return _quote(exchange, symbol, 'ticker');
  }

  function directLast(exchange, symbol) {
    const cfg = CONF[exchange];
    if (cfg && cfg.price) return _quote(exchange, symbol, 'price');
    return _quote(exchange, symbol, 'ticker').then((t) => t.last);
  }

  function num(v, d) {
    if (v === null || v === undefined || isNaN(v)) return null;
    if (d) return Number(v.toFixed(d));
    return Number(v);
  }

  /* Просчёт ордера прямо в браузере, источник данных — биржа. null — при неудаче. */
  async function directPreview(opts) {
    const { exchange, id, base, quote, unit, value, side, feeRate, leverage,
            minAmount, minNotional, precisionAmount, eurusdId } = opts;
    const v = parseFloat(value) || 0;
    if (!id || !conf_has(exchange)) return null;

    const tick = await _quote(exchange, id, 'ticker');
    const bid = parseFloat(tick.bid), ask = parseFloat(tick.ask), last = parseFloat(tick.last) || bid || ask;
    if ((!bid || isNaN(bid)) && (!ask || isNaN(ask)) && (!last || isNaN(last))) throw new Error('нет цены');

    let exec = side === 'buy' ? (ask || last) : (bid || last);
    if (!exec || isNaN(exec)) exec = last;

    let eurRate = null;
    if (String(quote).toUpperCase() === 'EUR') eurRate = 1.0;
    else if (eurusdId && conf_has(exchange)) {
      const eu = await _quote(exchange, eurusdId, 'ticker');
      const euLast = parseFloat(eu.last) || parseFloat(eu.bid) || parseFloat(eu.ask);
      if (euLast) eurRate = 1.0 / euLast;
    }

    let quoteValue = 0;
    if (unit === 'base') quoteValue = v * exec;
    else if (unit === 'eur') {
      if (!eurRate) throw new Error('EUR недоступен');
      quoteValue = v / eurRate;
    } else {
      quoteValue = v; // quote
    }
    const qty = quoteValue / exec;

    const notional = quoteValue * (leverage || 1);
    const feeQuote = notional * (feeRate || 0);
    const marginQuote = leverage && leverage > 0 ? quoteValue / leverage : quoteValue;

    let qtyRounded = qty;
    let digits = null;
    if (precisionAmount) {
      try { digits = precisionAmount >= 1 ? 0 : Math.max(0, Math.min(8, Math.round(-Math.log10(precisionAmount)))); } catch (e) { digits = null; }
    }
    if (digits !== null) qtyRounded = Number(qty.toFixed(digits));

    const warnings = [];
    if (minAmount && qtyRounded && qtyRounded > 0 && qtyRounded < Number(minAmount)) warnings.push('Количество меньше минимального ' + minAmount + ' ' + base);
    if (minNotional && quoteValue > 0 && quoteValue < Number(minNotional)) warnings.push('Номинал меньше минимального ' + minNotional + ' ' + quote);

    return {
      direct: true,
      exchange,
      pair: base + '/' + quote,
      base,
      quote,
      side,
      unit,
      value: num(v, 10),
      units: ['quote', 'base'].concat(eurRate ? ['eur'] : []),
      rate: {
        bid: num(bid, 8), ask: num(ask, 8), last: num(last, 8),
        mid: (bid && ask) ? num((bid + ask) / 2, 8) : null
      },
      exec_price: num(exec, 8),
      quote_value: num(quoteValue, 10),
      qty: num(qty, 12),
      qty_rounded: num(qtyRounded, 12),
      eur_rate: num(eurRate, 10),
      eur_value: num(quoteValue * eurRate, 4),
      notional_quote: num(notional, 8),
      fee_rate: feeRate,
      leverage: leverage,
      fee_quote: num(feeQuote, 10),
      fee_eur: num(feeQuote * eurRate, 4),
      margin_quote: num(marginQuote, 8),
      margin_eur: num(marginQuote * eurRate, 4),
      min_amount: minAmount,
      min_notional: minNotional,
      precision_amount: precisionAmount,
      warnings: warnings,
      ts: Date.now()
    };
  }

  function conf_has(exchange) { return !!CONF[exchange]; }
  function supported(exchange) { return conf_has(exchange); }

  /* ---- Прямые свечи (klines) с биржи, ccxt-стиль [[ts,o,h,l,c,v], ...] по возрастанию ---- */
  const KLINE_CONF = {
    binance: {
      url: (id, tf, lim) => `https://api.binance.com/api/v3/klines?symbol=${encodeURIComponent(id)}&interval=${tf}&limit=${lim}`,
      inter: (tf) => tf,
      parse: (j) => (j || []).map((k) => [Number(k[0]), Number(k[1]), Number(k[2]), Number(k[3]), Number(k[4]), Number(k[5])])
    },
    bybit: {
      url: (id, tf, lim) => `https://api.bybit.com/v5/market/kline?category=spot&symbol=${encodeURIComponent(id)}&interval=${tf}&limit=${lim}`,
      inter: (tf) => ({ '1m': '1', '5m': '5', '15m': '15', '1h': '60', '4h': '240', '1d': 'D', '1w': 'W' }[tf] || '60'),
      parse: (j) => {
        const arr = (((j.result || {}).list) || []).slice().reverse();
        return arr.map((k) => [Number(k.start), Number(k.open), Number(k.high), Number(k.low), Number(k.close), Number(k.volume)]);
      }
    },
    okx: {
      url: (id, tf, lim) => `https://www.okx.com/api/v5/market/candles?instId=${encodeURIComponent(id)}&bar=${tf}&limit=${lim}`,
      inter: (tf) => ({ '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W' }[tf] || '1H'),
      parse: (j) => (((j.data) || []).slice().reverse().map((k) => [Number(k[0]), Number(k[1]), Number(k[2]), Number(k[3]), Number(k[4]), Number(k[5])]))
    },
    bitfinex: {
      // свечи: [MTS, OPEN, CLOSE, HIGH, LOW, VOL]
      url: (id, tf, lim) => `https://api-pub.bitfinex.com/v2/candles/trade:${tf}:${encodeURIComponent(id)}/hist?limit=${lim}`,
      inter: (tf) => ({ '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1D', '1w': '1W' }[tf] || '1h'),
      parse: (j) => (j || []).map((k) => [Number(k[0]), Number(k[1]), Number(k[3]), Number(k[4]), Number(k[2]), Number(k[5])])
    },
    pionex: {
      url: (id, tf, lim) => `https://api.pionex.com/api/v1/market/klines?symbol=${encodeURIComponent(id)}&interval=${tf}&limit=${lim}`,
      inter: (tf) => ({ '1m': '1MN', '5m': '5M', '15m': '15M', '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W' }[tf] || '1H'),
      parse: (j) => (((j.data || {}).klines) || []).map((k) => [Number(k.time), Number(k.open), Number(k.high), Number(k.low), Number(k.close), Number(k.volume)])
    }
  };

  const DIRECT_INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'];

  async function klines(exchange, id, timeframe, limit) {
    const cfg = KLINE_CONF[exchange];
    if (!id || !cfg) throw new Error(exchange + ' direct klines недоступен');
    const tf = DIRECT_INTERVALS.indexOf(timeframe) >= 0 ? timeframe : '1h';
    const lim = Math.max(50, Math.min(parseInt(limit) || 500, 1000));
    const interval = cfg.inter(tf);
    const rows = cfg.parse(await get(cfg.url(id, interval, lim)));
    rows.sort((a, b) => a[0] - b[0]);
    if (!rows.length) throw new Error('пустые свечи ' + exchange + ' ' + id);
    return rows;
  }

  global.ExchangeFeed = {
    supported,
    directTicker,
    directLast,
    directPreview,
    klines
  };
})(window);