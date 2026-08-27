/* TradingView Lightweight Charts — professional candlestick + EMA */
let chartInstance = null;
let candleSeries = null;
let volumeSeries = null;
let ema7Series = null;
let ema25Series = null;
let ema99Series = null;

function calcEMA(data, period) {
    const k = 2 / (period + 1);
    const result = [];
    let ema = null;
    data.forEach((d, i) => {
        const val = d.close;
        ema = ema === null ? val : val * k + ema * (1 - k);
        if (i >= period - 1) result.push({ time: d.time, value: parseFloat(ema.toFixed(2)) });
    });
    return result;
}

function initTradingChart(containerId) {
    const container = document.getElementById(containerId);
    if (!container || typeof LightweightCharts === 'undefined') return null;
    if (chartInstance) { chartInstance.remove(); chartInstance = null; }

    const cs = getComputedStyle(document.body);
    const bg = cs.getPropertyValue('--bg-secondary').trim() || '#1a1d2e';
    const textColor = cs.getPropertyValue('--muted').trim() || '#9498b8';
    const gridColor = cs.getPropertyValue('--border').trim() || '#2a2e4a';

    chartInstance = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight || 400,
        layout: { background: { type: 'solid', color: bg }, textColor: textColor, fontSize: 11 },
        grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: gridColor, scaleMargins: { top: 0.05, bottom: 0.2 } },
        timeScale: { borderColor: gridColor, timeVisible: true, secondsVisible: false },
    });

    candleSeries = chartInstance.addCandlestickSeries({
        upColor: '#10b981', downColor: '#ef4444', borderUpColor: '#10b981',
        borderDownColor: '#ef4444', wickUpColor: '#10b981', wickDownColor: '#ef4444',
    });

    volumeSeries = chartInstance.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
    });
    chartInstance.priceScale('volume').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    ema7Series = chartInstance.addLineSeries({ color: '#fbbf24', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    ema25Series = chartInstance.addLineSeries({ color: '#6366f1', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    ema99Series = chartInstance.addLineSeries({ color: '#a855f7', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });

    new ResizeObserver(() => {
        if (chartInstance && container.clientWidth > 0) {
            chartInstance.applyOptions({ width: container.clientWidth, height: container.clientHeight || 400 });
        }
    }).observe(container);

    return chartInstance;
}

function loadChartData(pair, exchange, timeframe) {
    if (!candleSeries) return;
    const tf = timeframe === 'live' ? '1m' : timeframe;
    fetch(`/api/market/history?pair=${encodeURIComponent(pair)}&exchange=${encodeURIComponent(exchange)}&timeframe=${tf}`, {
        headers: { 'Accept': 'application/json' }
    })
    .then(r => r.json())
    .then(data => {
        if (!data.candles || !data.candles.length) return;
        const candles = data.candles.map(c => ({
            time: Math.floor(c.timestamp / 1000),
            open: Number(c.open), high: Number(c.high), low: Number(c.low), close: Number(c.close),
        }));
        candleSeries.setData(candles);

        const volumes = data.candles.map(c => ({
            time: Math.floor(c.timestamp / 1000),
            value: Number(c.volume || 0),
            color: c.close >= c.open ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)',
        }));
        volumeSeries.setData(volumes);

        if (candles.length >= 7) ema7Series.setData(calcEMA(candles, 7));
        if (candles.length >= 25) ema25Series.setData(calcEMA(candles, 25));
        if (candles.length >= 99) ema99Series.setData(calcEMA(candles, 99));

        updateOHLCV(candles[candles.length - 1]);
        updateTickerStats(data);
    })
    .catch(err => console.error('Chart load error:', err));
}

function updateOHLCV(candle) {
    const el = document.getElementById('term-ohlcv');
    if (!el || !candle) return;
    el.innerHTML = `<span>O <b>${candle.open.toFixed(2)}</b></span>` +
        `<span>H <b style="color:var(--success)">${candle.high.toFixed(2)}</b></span>` +
        `<span>L <b style="color:var(--danger)">${candle.low.toFixed(2)}</b></span>` +
        `<span>C <b>${candle.close.toFixed(2)}</b></span>` +
        `<span>Vol ${(candle.volume || 0).toLocaleString()}</span>`;
}

function updateTickerStats(data) {
    if (!data) return;
    const t = data.ticker || {};
    const priceEl = document.getElementById('term-price') || document.getElementById('test-price');
    const changeEl = document.getElementById('term-change') || document.getElementById('test-change');
    if (priceEl) {
        const price = t.last || 0;
        priceEl.textContent = price.toFixed(2);
        priceEl.className = 'term-pair-price ' + (t.percentage >= 0 ? 'up' : 'down');
    }
    if (changeEl) {
        const pct = t.percentage || 0;
        changeEl.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
        changeEl.className = 'term-pair-change ' + (pct >= 0 ? 'up' : 'down');
    }
    document.querySelectorAll('.term-stat-value[data-field]').forEach(el => {
        const f = el.dataset.field;
        if (f === 'vol24h' && t.quoteVolume) el.textContent = formatNum(t.quoteVolume);
        if (f === 'high24h' && t.high) el.textContent = t.high.toFixed(2);
        if (f === 'low24h' && t.low) el.textContent = t.low.toFixed(2);
        if (f === 'markPrice' && t.last) el.textContent = t.last.toFixed(2);
    });
}

function formatNum(n) {
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toFixed(2);
}

/* WebSocket live price updates */
let wsConn = null;
function startLivePrice(pair, exchange) {
    stopLivePrice();
    const symbol = pair.replace('/', '').toLowerCase();
    if (exchange.toLowerCase() === 'binance') {
        try {
            wsConn = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol}@trade`);
            wsConn.onmessage = e => {
                try {
                    const d = JSON.parse(e.data);
                    const price = parseFloat(d.p);
                    const priceEl = document.getElementById('term-price') || document.getElementById('test-price');
                    if (priceEl && price > 0) {
                        const prev = parseFloat(priceEl.dataset.prev || price);
                        priceEl.textContent = price.toFixed(2);
                        priceEl.className = 'term-pair-price ' + (price >= prev ? 'up' : 'down');
                        priceEl.dataset.prev = price;
                    }
                    if (candleSeries && price > 0) {
                        const now = Math.floor(Date.now() / 60000) * 60;
                        const last = candleSeries.data().at(-1);
                        if (last && last.time === now) {
                            candleSeries.update({ time: now, open: last.open, high: Math.max(last.high, price), low: Math.min(last.low, price), close: price });
                        } else {
                            candleSeries.update({ time: now, open: price, high: price, low: price, close: price });
                        }
                    }
                } catch (_) {}
            };
            wsConn.onclose = () => { if (wsConn) setTimeout(() => startLivePrice(pair, exchange), 3000); };
        } catch (_) {}
    }
}
function stopLivePrice() { if (wsConn) { try { wsConn.close(); } catch(_){} wsConn = null; } }
