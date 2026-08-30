/* TradingView Lightweight Charts — professional candlestick + indicators */
let chartInstance = null;
let candleSeries = null;
let volumeSeries = null;
let ema7Series = null;
let ema25Series = null;
let ema99Series = null;
let bbUpper = null;
let bbLower = null;
let bbMiddle = null;
let rsiSeries = null;

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

function calcSMA(data, period) {
    const result = [];
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
        sum += data[i].close;
        if (i >= period) sum -= data[i - period].close;
        if (i >= period - 1) result.push({ time: data[i].time, value: parseFloat((sum / period).toFixed(2)) });
    }
    return result;
}

function calcBollinger(data, period = 20, mult = 2) {
    const sma = calcSMA(data, period);
    const upper = [], lower = [], middle = [];
    for (let i = period - 1; i < data.length; i++) {
        const window = data.slice(i - period + 1, i + 1);
        const mean = window.reduce((s, d) => s + d.close, 0) / period;
        const variance = window.reduce((s, d) => s + (d.close - mean) ** 2, 0) / period;
        const sd = Math.sqrt(variance);
        const time = data[i].time;
        upper.push({ time, value: parseFloat((mean + mult * sd).toFixed(4)) });
        middle.push({ time, value: parseFloat(mean.toFixed(4)) });
        lower.push({ time, value: parseFloat((mean - mult * sd).toFixed(4)) });
    }
    return { upper, middle, lower };
}

function calcRSI(data, period = 14) {
    const result = [];
    let gain = 0, loss = 0;
    for (let i = 1; i < data.length; i++) {
        const delta = data[i].close - data[i - 1].close;
        if (i <= period) {
            gain += Math.max(delta, 0);
            loss += Math.max(-delta, 0);
            if (i === period) {
                gain /= period; loss /= period;
                result.push({ time: data[i].time, value: rsiValue(gain, loss) });
            }
            continue;
        }
        gain = (gain * (period - 1) + Math.max(delta, 0)) / period;
        loss = (loss * (period - 1) + Math.max(-delta, 0)) / period;
        result.push({ time: data[i].time, value: rsiValue(gain, loss) });
    }
    return result;
    function rsiValue(avgGain, avgLoss) {
        if (avgLoss === 0) return 100;
        return parseFloat((100 - 100 / (1 + avgGain / avgLoss)).toFixed(2));
    }
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
        rightPriceScale: { borderColor: gridColor, scaleMargins: { top: 0.05, bottom: 0.3 } },
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
    chartInstance.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    ema7Series = chartInstance.addLineSeries({ color: '#fbbf24', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    ema25Series = chartInstance.addLineSeries({ color: '#6366f1', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    ema99Series = chartInstance.addLineSeries({ color: '#a855f7', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });

    bbUpper = chartInstance.addLineSeries({ color: 'rgba(52,211,153,0.45)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    bbMiddle = chartInstance.addLineSeries({ color: 'rgba(52,211,153,0.25)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    bbLower = chartInstance.addLineSeries({ color: 'rgba(52,211,153,0.45)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });

    // RSI на отдельной нижней шкале (совместимо с v4 charts)
    rsiSeries = chartInstance.addLineSeries({
        color: '#22d3ee', lineWidth: 1, priceLineVisible: false, lastValueVisible: true,
        priceScaleId: 'rsi', title: 'RSI',
    });
    chartInstance.priceScale('rsi').applyOptions({ scaleMargins: { top: 0.75, bottom: 0, }, visible: true });
    rsiSeries.createPriceLine({ price: 70, color: '#ef4444', lineWidth: 1, lineStyle: 2, title: '70' });
    rsiSeries.createPriceLine({ price: 30, color: '#10b981', lineWidth: 1, lineStyle: 2, title: '30' });
    rsiSeries.createPriceLine({ price: 50, color: 'rgba(148,152,184,0.4)', lineWidth: 1, lineStyle: 3, title: '50' });

    new ResizeObserver(() => {
        if (chartInstance && container.clientWidth > 0) {
            chartInstance.applyOptions({ width: container.clientWidth, height: container.clientHeight || 400 });
        }
    }).observe(container);

    return chartInstance;
}

async function loadChartData(pair, exchange, timeframe) {
    if (!candleSeries) return;
    const tf = timeframe === 'live' ? '1m' : (timeframe || '1h');
    try {
        const r = await fetch(`/api/market/history?pair=${encodeURIComponent(pair)}&exchange=${encodeURIComponent(exchange)}&timeframe=${tf}`, {
            headers: { 'Accept': 'application/json' }
        });
        if (!r.ok) return;
        const data = await r.json();
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
        if (volumeSeries) volumeSeries.setData(volumes);

        if (candles.length >= 7) ema7Series.setData(calcEMA(candles, 7));
        if (candles.length >= 25) ema25Series.setData(calcEMA(candles, 25));
        if (candles.length >= 99) ema99Series.setData(calcEMA(candles, 99));

        if (candles.length >= 20) {
            const bb = calcBollinger(candles, 20, 2);
            bbUpper.setData(bb.upper); bbMiddle.setData(bb.middle); bbLower.setData(bb.lower);
        }
        if (candles.length >= 15 && rsiSeries) rsiSeries.setData(calcRSI(candles, 14));

        updateOHLCV(candles[candles.length - 1]);
        updateTickerStats(data);
    } catch (err) {
        console.error('Chart load error:', err);
    }
}

function updateOHLCV(candle) {
    document.querySelectorAll('#term-ohlcv, #test-ohlcv, #demo-ohlcv').forEach(el => {
        if (!el || !candle) return;
        el.innerHTML = `<span>O <b>${candle.open.toFixed(2)}</b></span>` +
            `<span>H <b style="color:var(--success)">${candle.high.toFixed(2)}</b></span>` +
            `<span>L <b style="color:var(--danger)">${candle.low.toFixed(2)}</b></span>` +
            `<span>C <b>${candle.close.toFixed(2)}</b></span>` +
            `<span>Vol ${(candle.volume || 0).toLocaleString()}</span>` +
            (candle.rsi ? `<span>RSI ${candle.rsi}</span>` : '');
    });
}

function updateTickerStats(data) {
    if (!data) return;
    const t = data.ticker || {};
    const priceEl = document.getElementById('term-price') || document.getElementById('test-price');
    const changeEl = document.getElementById('term-change') || document.getElementById('test-change');
    if (priceEl) {
        const price = t.last || 0;
        priceEl.textContent = price.toFixed(2);
        priceEl.className = 'term-pair-price ' + ((t.percentage || t.change) >= 0 ? 'up' : 'down');
    }
    if (changeEl) {
        const pct = t.change ?? t.percentage ?? 0;
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
