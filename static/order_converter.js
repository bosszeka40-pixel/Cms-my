/*
 * OrderConverter — профессиональный калькулятор терминала.
 *
 * Двусторонняя связь «сумма в USDT / EUR / монетах ⇄ количество монет» по живой ставке
 * биржи. Источник данных: напрямую публичный API биржи из браузера (ExchangeFeed.directPreview),
 * при недоступности — серверный /api/terminal/preview. Исполнение сделки всегда через сервер.
 *
 * create(cfg):
 *   host         — id контейнера, куда вставляется виджет
 *   pair()       — () => строка "BASE/QUOTE"
 *   exchange()   — () => название биржи
 *   mode()       — () => market_mode (spot/margin/futures)
 *   side()       — () => "buy"|"sell"
 *   leverage()   — () => число (плечо)
 *   balance()    — () => число (демо-баланс EUR, для кнопок %)
 *   onState()    — (state) => {} после каждого успешного просчёта
 *   onPairList() — (pairs, meta) => {} после загрузки /api/market/pairs
 *
 * Возвращает { getState, refresh, setUnit, setSide, exchangeChanged }
 *   getState() => { unit, value, preview|null }
 */
(function (global) {
  'use strict';

  const OCR = 'oc';
  const PAIR_LIST_CACHE = {}; // exchange -> meta

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }
  function num(v, d) {
    const f = d != null ? (v == null ? 0 : Number(v)).toFixed(d) : String(v == null ? '—' : v);
    return f;
  }

  class Widget {
    constructor(cfg) {
      this.cfg = cfg || {};
      this.state = { unit: 'quote', value: null, preview: null, error: null };
      this.meta = null;
      this._seq = 0;
      this._nice = (this.cfg.niceFormat || 0);
      this._render();
      this.loadPairList();
    }

    _el(id) { return document.getElementById(id); }

    _render() {
      const host = this._el(this.cfg.host);
      if (!host) return;
      host.classList.add(OCR + '-box');
      host.innerHTML = `
        <div class="${OCR}-chips" data-role="chips">
          <button type="button" class="${OCR}-chip active" data-unit="quote" title="Сумма в валюте котировки (USDT)">USDT</button>
          <button type="button" class="${OCR}-chip" data-unit="eur" title="Сумма в EUR — реальная стоимость монет">EUR</button>
          <button type="button" class="${OCR}-chip" data-unit="base" title="Количество монет">…</button>
        </div>
        <div class="${OCR}-fields">
          <div class="${OCR}-col">
            <label class="${OCR}-label" data-role="unit-label">Сумма (USDT)</label>
            <input data-role="value" type="number" step="any" min="0" placeholder="0.00" autocomplete="off">
            <div class="${OCR}-pcts">
              <button type="button" data-pct="25">25%</button>
              <button type="button" data-pct="50">50%</button>
              <button type="button" data-pct="75">75%</button>
              <button type="button" data-pct="100">100%</button>
            </div>
          </div>
          <span class="${OCR}-arrow">⇄</span>
          <div class="${OCR}-col">
            <label class="${OCR}-label" data-role="qty-label">Кол-во (монет)</label>
            <input data-role="qty" type="number" step="any" min="0" placeholder="0.00" autocomplete="off">
          </div>
        </div>
        <div class="${OCR}-info" data-role="info">⏳ Загрузка курса…</div>
      `;

      const chips = host.querySelector('[data-role="chips"]');
      chips.addEventListener('click', (e) => {
        const b = e.target.closest('.' + OCR + '-chip');
        if (b) this.setUnit(b.dataset.unit);
      });

      const valueEl = host.querySelector('[data-role="value"]');
      const qtyEl = host.querySelector('[data-role="qty"]');
      let t = null;
      const debounced = (fn) => {
        clearTimeout(t);
        t = setTimeout(fn, 220);
      };
      valueEl.addEventListener('input', () => { debounced(() => this._run(this.state.unit, valueEl.value)); });
      qtyEl.addEventListener('input', () => { debounced(() => this._run('base', qtyEl.value)); });

      host.querySelector('[data-role="pcts"]') && host.querySelectorAll('.' + OCR + '-pcts button').forEach((b) => {
        b.addEventListener('click', () => this._applyPct(parseFloat(b.dataset.pct)));
      });

      this.valueEl = valueEl;
      this.qtyEl = qtyEl;
    }

    setUnit(unit) {
      this.state.unit = unit;
      this._el(this.cfg.host) && Array.from(this._el(this.cfg.host).querySelectorAll('.' + OCR + '-chip')).forEach((b) => {
        b.classList.toggle('active', b.dataset.unit === unit);
      });
      const v = this.valueEl && this.valueEl.value;
      this._updateLabels();
      if (v) this._run(unit, v); else this.refresh();
    }

    setSide(side) {
      if (this._lastSide !== side) { this._lastSide = side; this.refresh(); }
    }

    _base() {
      const pair = (this.cfg.pair && this.cfg.pair()) || '';
      return pair.split('/')[0] || 'монет';
    }
    _quote() {
      const pair = (this.cfg.pair && this.cfg.pair()) || '';
      return pair.split('/')[1] || 'USDT';
    }

    _updateLabels() {
      const unit = this.state.unit;
      const h = this._el(this.cfg.host);
      if (!h) return;
      const ul = h.querySelector('[data-role="unit-label"]');
      const ql = h.querySelector('[data-role="qty-label"]');
      if (unit === 'quote') ul.textContent = 'Сумма (' + this._quote() + ')';
      else if (unit === 'eur') ul.textContent = 'Сумма (EUR)';
      else ul.textContent = 'Кол-во (' + this._base() + ')';
      ql.textContent = 'Кол-во (' + this._base() + ')';
      const baseChip = h.querySelector('.oc-chip[data-unit="base"]');
      if (baseChip) baseChip.textContent = this._base();
    }

    async loadPairList() {
      const exchange = (this.cfg.exchange && this.cfg.exchange()) || 'binance';
      const key = exchange.toLowerCase();
      const c = this.cfg;
      if (PAIR_LIST_CACHE[key] && PAIR_LIST_CACHE[key].ts + 300000 > Date.now()) {
        this._onPairs(PAIR_LIST_CACHE[key]);
        return;
      }
      try {
        const resp = await fetch('/api/market/pairs?exchange=' + encodeURIComponent(exchange), { cache: 'no-store' });
        if (!resp.ok) throw new Error(String(resp.status));
        const data = await resp.json();
        const meta = { exchange, pairs: data.pairs || [], fees: data.fees_by_mode || {}, leverage: data.leverage_max || {}, ts: Date.now() };
        PAIR_LIST_CACHE[key] = meta;
        this._onPairs(meta);
      } catch (e) {
        this.meta = null;
        if (c.onPairList) c.onPairList([], null);
      }
    }

    _onPairs(meta) {
      this.meta = meta;
      if (this.cfg.onPairList) this.cfg.onPairList(meta.pairs, meta);
      this._updateLabels();
      this.refresh();
    }

    exchangeChanged() { this.loadPairList(); }

    _pairMeta() {
      if (!this.meta || !this.meta.pairs) return null;
      const pair = (this.cfg.pair && this.cfg.pair()) || '';
      return this.meta.pairs.find((p) => p.pair === pair) || null;
    }

    _currentFee() {
      const mode = (this.cfg.mode && this.cfg.mode()) || 'spot';
      return (this.meta && this.meta.fees && this.meta.fees[mode]) || 0.001;
    }

    async refresh() {
      const v = this.valueEl && this.valueEl.value;
      return this._run(this.state.unit, v, true);
    }

    async _run(unit, rawValue, force) {
      if (unit !== 'base') this.state.unit = unit;
      const value = parseFloat(rawValue);
      const params = {
        exchange: (this.cfg.exchange && this.cfg.exchange()) || 'binance',
        pair: (this.cfg.pair && this.cfg.pair()) || 'BTC/USDT',
        mode: (this.cfg.mode && this.cfg.mode()) || 'spot',
        side: (this.cfg.side && this.cfg.side()) || 'buy',
        leverage: parseFloat((this.cfg.leverage && this.cfg.leverage()) || 1) || 1,
        unit, value: isNaN(value) ? 0 : value
      };
      const seq = ++this._seq;
      const infoEl = this._el(this.cfg.host) && this._el(this.cfg.host).querySelector('[data-role="info"]');

      let p = null;
      // 1) прямое API биржи из браузера (не грузим наш сервер)
      try {
        const meta = this._pairMeta();
        if (meta && meta.id && ExchangeFeed && ExchangeFeed.supported(params.exchange)) {
          const fm = this.meta && this.meta;
          const eurusd = (fm && fm.pairs || []).find((x) => x.pair === 'EUR/USDT');
          p = await ExchangeFeed.directPreview({
            exchange: params.exchange, id: meta.id, base: meta.base, quote: meta.quote,
            unit, value: params.value, side: params.side,
            feeRate: this._currentFee(), leverage: params.leverage,
            minAmount: meta.min_amount, minNotional: meta.min_notional,
            precisionAmount: meta.precision_amount, eurusdId: eurusd && eurusd.id
          });
        }
      } catch (e) { p = null; }

      // 2) серверный fallback (данные всё равно с биржи через ccxt)
      if (!p) {
        try {
          const u = '/api/terminal/preview?pair=' + encodeURIComponent(params.pair) +
            '&exchange=' + encodeURIComponent(params.exchange) +
            '&market_mode=' + encodeURIComponent(params.mode) +
            '&side=' + encodeURIComponent(params.side) +
            '&unit=' + unit + '&value=' + encodeURIComponent(String(params.value)) +
            '&leverage=' + encodeURIComponent(String(params.leverage));
          const resp = await fetch(u, { cache: 'no-store' });
          if (resp.ok) { p = await resp.json(); p.direct = false; }
          else { throw new Error((await resp.json().catch(() => ({}))).detail || String(resp.status)); }
        } catch (e) {
          if (seq !== this._seq) return;
          this.state = { unit: this.state.unit, value: params.value, preview: null, error: String(e && e.message || e) };
          if (infoEl) infoEl.textContent = '⚠ ' + esc(String(e && e.message || 'курс недоступен')) + ' — проверьте подключение биржи';
          if (this.cfg.onState) this.cfg.onState(this.getState());
          return;
        }
      }
      if (!p) return;
      if (seq !== this._seq) return;

      this.state = { unit, value: params.value, preview: p, error: null };

      // Синхронизация парных полей
      if (unit === 'base') {
        if (this.valueEl && p.eur_value != null) {
          if (this.state.unit === 'eur') this.valueEl.value = num(p.eur_value, this._nice);
          else if (this.state.unit === 'quote') this.valueEl.value = num(p.quote_value, this._nice);
          else this.valueEl.value = num(p.qty_rounded, 10);
        }
      } else if (this.qtyEl && p.qty_rounded != null) {
        this.qtyEl.value = num(p.qty_rounded, 10) === '0' ? '' : num(p.qty_rounded, 10);
      }
      if (infoEl) this._renderInfo(infoEl, p);
      if (this.cfg.onState) this.cfg.onState(this.getState());
    }

    _renderInfo(el, p) {
      const q = p.quote, b = p.base;
      const side = p.side === 'buy' ? 'Покупка' : 'Продажа';
      const unitName = p.unit === 'quote' ? q : p.unit === 'eur' ? 'EUR' : b;
      const rate = p.rate || {};
      const ee = p.exec_price;
      const feeColor = 'var(--warning)';
      let rows = '';
      rows += '<div class="' + OCR + '-row"><span>Ставка биржи</span><span><b>' + (ee != null ? num(ee, 8) : '—') + '</b> ' + q +
        ' <span style="color:var(--text-muted)">(bid ' + num(rate.bid, 8) + ' · ask ' + num(rate.ask, 8) + ')</span></span></div>';
      if (p.unit === 'base') {
        rows += '<div class="' + OCR + '-row"><span>В ' + q + '</span><span><b>' + num(p.quote_value, 4) + ' ' + esc(q) + '</b></span></div>';
      } else {
        rows += '<div class="' + OCR + '-row"><span>' + (p.unit === 'eur' ? 'В ' + q : 'Кол-во') + '</span><span><b>' + num(p.qty_rounded, 10) + ' ' + esc(b) + '</b></span></div>';
      }
      rows += '<div class="' + OCR + '-row"><span>Стоимость в EUR</span><span><b>' + (p.eur_value != null ? num(p.eur_value, 4) + ' €' : '—') + '</b></span></div>';
      rows += '<div class="' + OCR + '-row"><span>Комиссия (' + ((p.fee_rate || 0) * 100).toFixed(3) + '%)</span><span style="color:' + feeColor + '">' +
        (p.fee_quote != null ? num(p.fee_quote, 6) + ' ' + esc(q) + (p.fee_eur != null ? ' · ' + num(p.fee_eur, 4) + ' €' : '') : '—') + '</span></div>';
      rows += '<div class="' + OCR + '-row"><span>Маржа (плечо ' + num(p.leverage, 1) + 'x)</span><span>' +
        (p.margin_quote != null ? num(p.margin_quote, 4) + ' ' + esc(q) + (p.margin_eur != null ? ' · ' + num(p.margin_eur, 4) + ' €' : '') : '—') + '</span></div>';
      rows += '<div class="' + OCR + '-row"><span>Лимиты</span><span style="color:var(--text-muted)">' +
        (p.min_amount != null ? 'лот ≥ ' + num(p.min_amount, 8) + ' ' + esc(b) : '') +
        (p.min_notional != null ? ' · номинал ≥ ' + num(p.min_notional, 8) + ' ' + esc(q) : '') + '</span></div>';
      if (p.direct) rows += '<div class="' + OCR + '-row"><span>Источник</span><span style="color:var(--success)">' + esc(p.exchange) + ' · прямое API биржи</span></div>';
      const warns = (p.warnings || []).map((w) => '<div class="' + OCR + '-warn">⚠ ' + esc(w) + '</div>').join('');
      el.innerHTML = warns + rows;
    }

    async _applyPct(pct) {
      const bal = parseFloat((this.cfg.balance && this.cfg.balance()) || 0);
      if (!bal) return;
      const p = this.state.preview;
      if (!p || !p.eur_rate) { // без курса просто ставим % баланса в EUR
        if (this.state.unit === 'eur' && this.valueEl) this.valueEl.value = num(bal * pct / 100, 2);
        return this._run(this.state.unit, this.valueEl && this.valueEl.value);
      }
      const eurValue = bal * pct / 100;
      let val;
      if (this.state.unit === 'eur') val = eurValue;
      else if (this.state.unit === 'quote') val = eurValue / p.eur_rate;
      else val = eurValue / ((p.rate && (p.side === 'buy' ? p.rate.ask : p.rate.bid)) || p.exec_price) / p.eur_rate;
      if (this.valueEl) this.valueEl.value = num(val, 10) === '0' ? '' : num(val, 10);
      this.valueEl && this.valueEl.blur();
      this._run(this.state.unit, this.valueEl && this.valueEl.value);
    }

    getState() {
      return { unit: this.state.unit, value: this.state.value, preview: this.state.preview };
    }
  }

  global.OrderConverter = {
    create(cfg) { return new Widget(cfg); },
    _cache: PAIR_LIST_CACHE
  };
})(window);