(() => {
  const button = document.getElementById('refresh-market');
  const pair = document.getElementById('market-pair');
  const exchange = document.getElementById('market-exchange');
  const timeframe = document.getElementById('market-timeframe');
  if (!button || !pair || !exchange || !timeframe) return;

  button.addEventListener('click', async (event) => {
    event.preventDefault();
    event.stopImmediatePropagation();
    const ticker = document.getElementById('ticker');
    try {
      ticker.textContent = 'Загружаем данные...';
      const response = await fetch(`/api/market/data?pair=${encodeURIComponent(pair.value)}&exchange=${encodeURIComponent(exchange.value)}`, {headers: {Accept: 'application/json'}});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Ошибка загрузки котировок');
      document.getElementById('market-source').textContent = `${data.exchange} · live`;
      ticker.innerHTML = `Цена: <strong>${Number(data.ticker.last).toFixed(2)}</strong> · Изменение: ${Number(data.ticker.change || 0).toFixed(2)}%`;
      const price = document.getElementById('manual-price');
      if (price) price.value = data.ticker.last || '';
      const render = (id, levels) => { const node = document.getElementById(id); node.innerHTML = (levels || []).map(level => `<div class="book-row"><span>${Number(level[0]).toFixed(2)}</span><span>${Number(level[1]).toFixed(5)}</span></div>`).join('') || 'Нет данных'; };
      render('bids', data.order_book?.bids); render('asks', data.order_book?.asks);
      button.textContent = 'Котировки обновлены';
      setTimeout(() => { button.textContent = 'Загрузить котировки'; }, 1200);
    } catch (error) { ticker.textContent = error.message; }
  }, true);
})();
