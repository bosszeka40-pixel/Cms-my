/* ApiUI — общие примитивы для красивого отображения API-данных */
window.ApiUI = (function () {
    var ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    function esc(s) { return String(s ?? '').replace(/[&<>"']/g, function (c) { return ESC[c]; }); }

    function num(n, d) {
        var v = Number(n);
        if (!Number.isFinite(v)) return '—';
        return v.toLocaleString('ru-RU', { maximumFractionDigits: (d === undefined ? 2 : d), minimumFractionDigits: (d === undefined ? 2 : d) });
    }
    function num6(n) { return num(n, 6); }
    function pct(n, d) {
        if (!Number.isFinite(Number(n))) return '—';
        return (Number(n) > 0 ? '+' : '') + Number(n).toFixed(d === undefined ? 2 : d) + '%';
    }
    function signColor(v) {
        var n = Number(v);
        return n > 0 ? 'var(--success)' : n < 0 ? 'var(--danger)' : 'var(--text-secondary)';
    }
    function time(ts) {
        if (!ts && ts !== 0) return '—';
        var d = new Date(typeof ts === 'number' ? ts : String(ts));
        if (isNaN(d.getTime())) return esc(String(ts).slice(0, 16).replace('T', ' '));
        return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    }

    var LABELS = {
        monthly_return_pct: 'Доходность/мес', final_balance_eur: 'Итоговый баланс', initial_balance_eur: 'Старт. баланс',
        win_rate_pct: 'Сделки в плюс', max_drawdown_pct: 'Макс. просадка', sharpe: 'Sharpe', sortino: 'Sortino',
        profit_factor: 'Profit Factor', trades: 'Сделок', price_eur: 'Цена', as_of: 'Данные от', data_days: 'Дней данных',
        data_source: 'Источник', category: 'Категория', leverage: 'Леверидж', risk_tolerance: 'Риск', fee_rate: 'Комиссия',
        log_level: 'Лог', strategy: 'Стратегия', signal: 'Сигнал', pnl: 'P/L', pl: 'P/L', balance: 'Баланс',
        entry_price: 'Вход', exit_price: 'Выход', risk_score: 'Скор риска', confidence: 'Уверенность',
        generated_count: 'Сгенерировано', published_count: 'Опубликовано', last_generation: 'Последняя генерация',
        total_trades: 'Всего сделок', avg_pnl: 'Средний P/L', win_rate: 'Винрейт', strategies_used: 'Стратегии',
        kill_switch: 'Kill Switch', daily_pnl: 'Дневной P/L', peak_balance: 'Пиковый баланс', risk_per_trade: 'Риск/сделку',
        daily_loss_limit: 'Лимит просадки/день', max_drawdown: 'Макс. просадка', max_leverage: 'Макс. плечо',
        current_risk_score: 'Текущий скор', max_risk_score: 'Порог скора', users: 'Пользователей', strategies: 'Стратегий',
        status: 'Статус', site_name: 'Название сайта', support_contact: 'Поддержка', maintenance_mode: 'Обслуживание',
        order_id: 'ID ордера', market: 'Инструмент', mode: 'Режим', description: 'Описание', owner: 'Владелец',
        is_public: 'Публичная', trial_days: 'Дней пробного', strategy_type: 'Тип', generated: 'Сгенерировано',
        winners: 'Победителей', published: 'Опубликовано', best_return: 'Лучшая доходность', return: 'Доходность'
    };
    function pretty(k) { return LABELS[String(k)] || String(k).replace(/_/g, ' '); }

    function badge(text, tone) {
        var tones = { ok: 'badge-success', bad: 'badge-danger', warn: 'badge-warning', info: 'badge-accent', flat: 'badge' };
        return '<span class="' + (tones[tone] || 'badge') + '" style="padding:.2rem .55rem;border-radius:999px;font-size:.68rem;font-weight:600;white-space:nowrap;">' + esc(text) + '</span>';
    }

    function formatValue(val) {
        if (val === null || val === undefined || val === '') return '—';
        if (typeof val === 'boolean') return badge(val ? 'Да' : 'Нет', val ? 'ok' : 'flat');
        if (typeof val === 'number') return '<span style="font-family:var(--font-mono);">' + num6(val) + '</span>';
        if (String(val) === 'true' || String(val) === 'false' || String(val) === 'on' || String(val) === 'off') {
            var on = val === 'true' || val === 'on';
            return badge(on ? 'ВКЛ' : 'ВЫКЛ', on ? 'ok' : 'flat');
        }
        var s = String(val);
        if (s.slice(-1) === '%') {
            var nn = Number(s);
            return '<span style="font-family:var(--font-mono);color:' + (nn > 0 ? 'var(--success)' : nn < 0 ? 'var(--danger)' : 'inherit') + ';">' + pct(nn, 2) + '</span>';
        }
        return esc(s);
    }

    function kvRow(label, valueHtml, valueColor) {
        return '<div class="api-kv"><span class="api-kv-k">' + esc(label) + '</span><span class="api-kv-v" style="' + (valueColor ? 'color:' + valueColor + ';' : '') + '">' + valueHtml + '</span></div>';
    }
    function kv(obj) {
        if (obj === null || obj === undefined) return '<div class="term-empty">Нет данных</div>';
        if (typeof obj !== 'object') return formatValue(obj);
        return Object.keys(obj).map(function (k) {
            var v = obj[k];
            if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
                return '<div style="margin:.35rem .5rem;background:var(--bg-tertiary);border:1px solid var(--border);border-radius:var(--radius-sm);">' +
                    '<div style="padding:.45rem .6rem .2rem;font-size:.64rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.03em;">' + esc(pretty(k)) + '</div>' +
                    kv(v) + '</div>';
            }
            return kvRow(pretty(k), formatValue(v), null);
        }).join('');
    }

    function statGrid(stats) {
        return '<div class="api-stat-grid">' + stats.map(function (s) {
            return '<div class="api-stat"><div class="api-stat-label">' + esc(s.label) + '</div>' +
                '<div class="api-stat-value" style="' + (s.color ? 'color:' + s.color + ';' : '') + '">' + s.value + '</div>' +
                (s.sub ? '<div class="api-stat-sub">' + esc(s.sub) + '</div>' : '') + '</div>';
        }).join('') + '</div>';
    }

    function gauge(value, max, label, warn) {
        var v = Number(value) || 0;
        var m = Number(max) || 1;
        var p = Math.max(0, Math.min(100, (v / m) * 100));
        var color = warn ? (p >= 75 ? 'var(--danger)' : p >= 45 ? 'var(--warning)' : 'var(--success)') : 'var(--primary)';
        return '<div style="margin:.3rem 0;">' +
            (label ? '<div style="display:flex;justify-content:space-between;font-size:.68rem;margin-bottom:.25rem;"><span style="color:var(--text-muted);text-transform:uppercase;letter-spacing:.02em;">' + esc(label) + '</span><span style="font-weight:700;color:' + color + ';font-family:var(--font-mono);">' + esc(value === '' || value === undefined ? '—' : value) + (m && m !== 1 ? ' / ' + esc(max) : '') + '</span></div>' : '') +
            '<div class="api-progress"><i style="width:' + p + '%;background:' + color + ';"></i></div></div>';
    }

    function rowCell(c) {
        if (c === null || c === undefined) return '<td class="api-muted">—</td>';
        if (typeof c === 'object') {
            var html = c.html !== undefined ? c.html : '—';
            return '<td style="' + (c.style || '') + '">' + html + '</td>';
        }
        return '<td>' + esc(String(c)) + '</td>';
    }
    function table(headers, rows) {
        if (!rows || !rows.length) return '<div class="term-empty">Нет данных</div>';
        return '<div style="overflow-x:auto;"><table class="api-table"><thead><tr>' +
            headers.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') + '</tr></thead><tbody>' +
            rows.map(function (r) { return '<tr>' + r.map(rowCell).join('') + '</tr>'; }).join('') +
            '</tbody></table></div>';
    }

    function cellNum(v) { return { html: esc(num6(v)), style: 'font-family:var(--font-mono);' }; }
    function cellColored(v, unit) {
        var n = Number(v);
        if (!Number.isFinite(n)) return { html: '—', style: '' };
        return { html: esc(pct(n, 2)) + (unit || ''), style: 'color:' + signColor(n) + ';font-weight:600;font-family:var(--font-mono);' };
    }
    function cellPct(v) {
        var n = Number(v);
        if (!Number.isFinite(n)) return { html: '—', style: '' };
        return { html: esc(pct(n, 1)), style: 'color:' + signColor(n) + ';font-weight:600;font-family:var(--font-mono);' };
    }
    function cellTime(ts) { return { html: time(ts), style: 'color:var(--text-muted);white-space:nowrap;font-size:.72rem;' }; }

    return {
        esc: esc, num: num, num6: num6, pct: pct, signColor: signColor, time: time,
        pretty: pretty, badge: badge, formatValue: formatValue,
        kvRow: kvRow, kv: kv,
        statGrid: statGrid, gauge: gauge, table: table,
        cellNum: cellNum, cellColored: cellColored, cellPct: cellPct, cellTime: cellTime
    };
})();