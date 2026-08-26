(() => {
  const pairSelect = document.getElementById('pair');
  const marketPair = document.getElementById('market-pair');
  const exchangeSelect = document.getElementById('exchange');
  const marketExchange = document.getElementById('market-exchange');
  const activePair = () => (pairSelect || marketPair)?.value;
  const activeExchange = () => (exchangeSelect || marketExchange)?.value;
  const setBusy = (element, text) => { if (element) { element.disabled = true; element.textContent = text; } };
  const setIdle = (element, text) => { if (element) { element.disabled = false; element.textContent = text; } };

  function drawCandles(candles) {
    const canvas = document.getElementById('price-chart');
    if (!canvas) return;
    const context = canvas.getContext('2d');
    const width = canvas.clientWidth || 600;
    canvas.width = width * 2;
    canvas.height = Number(canvas.getAttribute('height')) * 2;
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!candles?.length) return;
    const values = candles.flatMap(([, open, high, low, close]) => [open, high, low, close].map(Number));
    const minimum = Math.min(...values), maximum = Math.max(...values);
    const range = Math.max(maximum - minimum, 1e-9);
    const slot = canvas.width / candles.length;
    const bodyWidth = Math.max(2, slot * .45);
    const toY = value => 15 + (1 - (value - minimum) / range) * (canvas.height - 30);
    candles.forEach((candle, index) => {
      const [, open, high, low, close] = candle.map(Number);
      const x = index * slot + slot / 2;
      const up = close >= open;
      context.strokeStyle = context.fillStyle = up ? '#16a34a' : '#dc2626';
      context.lineWidth = 2;
      context.beginPath(); context.moveTo(x, toY(high)); context.lineTo(x, toY(low)); context.stroke();
      const top = Math.min(toY(open), toY(close));
      context.fillRect(x - bodyWidth / 2, top, bodyWidth, Math.max(1, Math.abs(toY(close) - toY(open))));
    });
  }

  function drawBalanceChart(trades) {
    const canvas = document.getElementById('balance-chart');
    if (!canvas) return;
    const context = canvas.getContext('2d');
    const width = canvas.clientWidth || 600;
    canvas.width = width * 2; canvas.height = 400;
    context.clearRect(0, 0, canvas.width, canvas.height);
    const points = (trades || []).slice().reverse();
    if (points.length < 2) return;
    const values = points.map(point => Number(point.balance));
    const minimum = Math.min(...values), maximum = Math.max(...values);
    const range = Math.max(maximum - minimum, 1e-9);
    const stepX = canvas.width / (points.length - 1);
    const toY = value => 20 + (1 - (value - minimum) / range) * (canvas.height - 40);
    context.strokeStyle = getComputedStyle(document.body).getPropertyValue('--primary');
    context.lineWidth = 4; context.beginPath();
    points.forEach((point, index) => { const x = index * stepX, y = toY(Number(point.balance)); index ? context.lineTo(x, y) : context.moveTo(x, y); });
    context.stroke();
  }

  async function loadHistory() {
    const table = document.getElementById('trade-history');
    if (!table) return;
    try {
      const response = await fetch('/api/trading/history');
      if (!response.ok) return;
      const data = await response.json();
      table.innerHTML = data.trades.map(trade => `<tr><td>${trade.created_at}</td><td>${trade.mode}</td><td>${trade.pair}</td><td>${trade.strategy}</td><td>${Number(trade.pnl).toFixed(4)}</td><td>${Number(trade.balance).toFixed(2)}</td></tr>`).join('') || '<tr><td colspan="6">Сделок пока нет.</td></tr>';
      drawBalanceChart(data.trades);
    } catch {}
  }

  async function loadMarketData() {
    const tickerBox = document.getElementById('ticker');
    if (!tickerBox || !activePair()) return;
    tickerBox.textContent = 'Загружаем данные...';
    try {
      const query = `pair=${encodeURIComponent(activePair())}&exchange=${encodeURIComponent(activeExchange())}`;
      const timeframe = document.getElementById('market-timeframe')?.value || '1h';
      const [tickerResponse, historyResponse] = await Promise.all([
        fetch(`/api/market/data?${query}`),
        fetch(`/api/market/history?${query}&timeframe=${encodeURIComponent(timeframe)}`)
      ]);
      const ticker = await tickerResponse.json();
      const history = await historyResponse.json();
      if (!tickerResponse.ok) throw new Error(ticker.detail || 'Ошибка котировок');
      if (!historyResponse.ok) throw new Error(history.detail || 'Ошибка свечей');
      document.getElementById('market-source').textContent = `${ticker.exchange} · live`;
      tickerBox.innerHTML = `Цена: <strong>${Number(ticker.ticker.last).toFixed(2)}</strong> · изменение ${Number(ticker.ticker.change || 0).toFixed(2)}%`;
      const price = document.getElementById('manual-price'); if (price && ticker.ticker.last) price.value = ticker.ticker.last;
      const renderLevels = target => document.getElementById(target)?.replaceChildren();
      renderLevels('bids'); renderLevels('asks');
      ['bids', 'asks'].forEach(target => {
        const box = document.getElementById(target); if (!box) return;
        box.innerHTML = (ticker.order_book[target] || []).slice(0, 8).map(([price, amount]) => `<div class="book-row"><span>${Number(price).toFixed(2)}</span><span>${Number(amount).toFixed(6)}</span></div>`).join('');
      });
      drawCandles(history.candles);
    } catch (error) { tickerBox.textContent = error.message; }
  }

  async function loadSignal() {
    const box = document.getElementById('signal-result'); if (!box) return;
    box.textContent = 'Рассчитываем сигнал...';
    try {
      const response = await fetch(`/api/market/signal?pair=${encodeURIComponent(activePair())}&exchange=${encodeURIComponent(activeExchange())}`);
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Ошибка сигнала');
      const direction = {1:'ПОКУПКА', '-1':'ПРОДАЖА', 0:'ОЖДАНИЕ'}[data.signal] || 'ОЖИДАНИЕ';
      box.innerHTML = `${direction}: ${data.strategy}, уверенность ${Math.round(data.confidence * 100)}%.`;
    } catch (error) { box.textContent = error.message; }
  }

  async function loadNews() {
    const list = document.getElementById('news-list'); if (!list) return;
    list.textContent = 'Загружаем новости...';
    try {
      const response = await fetch('/api/market/news?limit=5'); const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Ошибка новостей');
      const sentiment = document.getElementById('news-sentiment');
      if (sentiment) sentiment.textContent = `сентимент ${Number(data.sentiment).toFixed(2)}`;
      list.innerHTML = (data.news || []).map(item => `<p>${item.title}</p>`).join('') || 'Свежих новостей нет.';
    } catch (error) { list.textContent = error.message; }
  }

  async function loadRisk() {
    const box = document.getElementById('risk-status'); if (!box) return;
    try {
      const response = await fetch('/api/risk/status'); const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Ошибка риска');
      const pill = document.getElementById('risk-kill-switch');
      if (pill) pill.textContent = data.kill_switch ? 'остановлено' : 'разрешено';
      box.innerHTML = `Дневной P/L: <strong>${Number(data.daily_pnl).toFixed(4)}</strong> · лимит ${(data.daily_loss_limit * 100).toFixed(1)}% · плечо ${data.max_leverage}`;
    } catch (error) { box.textContent = error.message; }
  }

  async function refreshBotStatus() {
    if (!document.getElementById('bot-active')) return;
    try {
      const response = await fetch('/api/bot/status'); if (!response.ok) return;
      const data = await response.json();
      document.getElementById('bot-active').textContent = data.active ? 'запущен' : 'остановлен';
      document.getElementById('bot-runs').textContent = data.runs;
      const log = document.getElementById('bot-log');
      log.innerHTML = (data.stats || []).slice(-10).reverse().map(event => `<p>${event.time} — ${event.event}${event.pair ? `: ${event.pair}, сигнал ${event.signal}, P/L ${Number(event.pl).toFixed(4)}` : ''}</p>`).join('');
    } catch {}
  }

  document.getElementById('refresh-market')?.addEventListener('click', loadMarketData);
  document.getElementById('get-signal')?.addEventListener('click', loadSignal);
  document.getElementById('refresh-news')?.addEventListener('click', loadNews);
  [document.getElementById('market-pair'), document.getElementById('market-exchange'), document.getElementById('market-timeframe')].forEach(item => item?.addEventListener('change', loadMarketData));

  document.getElementById('manual-trade-form')?.addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget;
    const payload = {pair: activePair(), side: document.getElementById('manual-side').value};
    ['manual-price','manual-amount','manual-balance'].forEach(id => payload[id.replace('manual-', '')] = Number(document.getElementById(id).value));
    try {
      const response = await fetch('/api/trading/manual', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Ошибка исполнения');
      document.getElementById('manual-result').textContent = `Исполнено. Комиссия ${Number(data.fee).toFixed(4)}, баланс ${Number(data.balance).toFixed(2)}.`;
      loadHistory();
    } catch (error) { document.getElementById('manual-result').textContent = error.message; }
  });

  document.getElementById('trade-test-form')?.addEventListener('submit', async event => {
    event.preventDefault(); const button = document.getElementById('test-submit'), result = document.getElementById('trade-result');
    setBusy(button, 'Тестирование...');
    result.hidden = false; result.textContent = 'Расчёт...';
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    ['news_sentiment','price_change','current_balance'].forEach(key => payload[key] = Number(payload[key]));
    try {
      const response = await fetch('/api/trading/test', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Ошибка теста');
      result.innerHTML = `<h3>Результат</h3><p>Сигнал: <strong>${data.signal}</strong> · P/L <strong>${Number(data.trade.pl).toFixed(2)}</strong></p><p>Баланс: <strong>${Number(data.next_balance).toFixed(2)}</strong></p>`;
      loadHistory(); refreshBotStatus();
    } catch (error) { result.textContent = error.message; }
    finally { setIdle(button, 'Запустить тест'); }
  });

  document.getElementById('run-backtest')?.addEventListener('click', async event => {
    const button = event.currentTarget, output = document.getElementById('backtest-result');
    setBusy(button, 'Тестирование...'); output.textContent = 'Расчёт backtest...';
    try {
      const response = await fetch('/api/bot/backtest', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({pair:activePair(), exchange:activeExchange(), initial_balance:10})});
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Ошибка backtest');
      output.innerHTML = `<table><thead><tr><th>Стратегия</th><th>Баланс</th><th>P/L</th><th>ROI</th><th>Победы</th></tr></thead><tbody>${data.results.map(item => `<tr><td>${item.strategy}</td><td>${item.final_balance.toFixed(2)}</td><td>${item.pnl.toFixed(2)}</td><td>${item.roi.toFixed(2)}%</td><td>${item.wins}/${item.trades}</td></tr>`).join('')}</tbody></table>`;
    } catch (error) { output.innerHTML = `<div class="message">${error.message}</div>`; }
    finally { setIdle(button, 'Запустить 365 дней'); }
  });

  drawBalanceChart(JSON.parse(document.getElementById('balance-chart')?.dataset.trades || '[]'));
  loadMarketData(); loadHistory(); loadNews(); loadRisk(); refreshBotStatus();
  setInterval(refreshBotStatus, 8000);
})();
