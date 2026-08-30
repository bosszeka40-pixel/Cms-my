/* Реальный стакан (order book) из /api/market/orderbook + метрики ликвидности */
(function (global) {
    let timers = [];
    let lastContainer = null;

    function stopAll() {
        timers.forEach(t => clearInterval(t));
        timers = [];
    }

    function buildBlock(levels, side) {
        if (!levels || !levels.length) return '<div class="term-empty">Нет данных</div>';
        const maxVol = Math.max(...levels.map(l => l[1]));
        return levels.map(([price, volume]) => {
            const bar = (volume / maxVol) * 100;
            return '<div class="ob-row">' +
                '<span class="ob-price" style="color:' + (side === 'ask' ? 'var(--danger)' : 'var(--success)') + '">' + price.toFixed(price >= 1000 ? 1 : price >= 100 ? 2 : 4) + '</span>' +
                '<span class="ob-bar"><span class="ob-fill" style="width:' + bar.toFixed(1) + '%;background:' + (side === 'ask' ? 'rgba(239,68,68,.18)' : 'rgba(16,185,129,.18)') + '"></span></span>' +
                '<span class="ob-vol">' + formatNumLite(volume) + '</span>' +
                '</div>';
        }).join('');
    }

    function formatNumLite(n) {
        if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
        if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
        return n.toFixed(n < 10 ? 4 : 2);
    }

    function render(payload, target) {
        const bids = payload.bids || [];
        const asks = payload.asks || [];
        const bestBid = bids.length ? bids[0][0] : null;
        const bestAsk = asks.length ? asks[0][0] : null;
        const mid = bestBid && bestAsk ? (bestBid + bestAsk) / 2 : (bestBid || bestAsk);
        const spread = bestBid && bestAsk ? bestAsk - bestBid : 0;
        const spreadPct = mid ? (spread / mid) * 100 : 0;
        const bidVol = bids.reduce((s, l) => s + l[1], 0);
        const askVol = asks.reduce((s, l) => s + l[1], 0);
        const imb = bidVol + askVol > 0 ? ((bidVol - askVol) / (bidVol + askVol)) * 100 : 0;

        target.innerHTML =
            '<div class="ob-head">' +
            '<span class="ob-head-l">Бид ' + (bestBid ? bestBid.toFixed(4) : '—') + ' / Аск ' + (bestAsk ? bestAsk.toFixed(4) : '—') + '</span>' +
            '<span class="ob-spread">Спред ' + (spreadPct * 100 || 0).toFixed(3) + '%</span>' +
            '</div>' +
            '<div class="ob-asks">' + buildBlock(asks.slice().reverse(), 'ask') + '</div>' +
            '<div class="ob-mid">' + (mid ? formatNumLite(mid) : '—') + '</div>' +
            '<div class="ob-bids">' + buildBlock(bids, 'bid') + '</div>' +
            '<div class="ob-foot">' +
            '<span>Покупка ' + formatNumLite(bidVol) + '</span>' +
            '<span>Продажа ' + formatNumLite(askVol) + '</span>' +
            '<span class="ob-imb">Дисбаланс ' + (imb >= 0 ? '+' : '') + imb.toFixed(1) + '%</span>' +
            '</div>';
    }

    async function fetchBook(pair, exchange, opts) {
        const target = document.getElementById(opts.containerId);
        if (!target) return;
        try {
            const r = await fetch('/api/market/orderbook?pair=' + encodeURIComponent(pair) + '&exchange=' + encodeURIComponent(exchange) + '&limit=12', { headers: { 'Accept': 'application/json' } });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            render(data, target);
        } catch (_) {
            target.innerHTML = '<div class="term-empty">Стакан недоступен (проверьте биржу)</div>';
        }
    }

    global.OrderBookPanel = {
        init(opts) {
            lastContainer = opts.containerId;
            stopAll();
            const refresh = () => fetchBook(opts.pair, opts.exchange, opts);
            refresh();
            timers.push(setInterval(refresh, 3500));
            return refresh;
        },
        setPair(pair, exchange) {
            stopAll();
            const refresh = () => fetchBook(pair, exchange, { containerId: lastContainer });
            refresh();
            timers.push(setInterval(refresh, 3500));
        },
        stop() { stopAll(); },
        buildBlock,
        formatNumLite,
    };
})(window);