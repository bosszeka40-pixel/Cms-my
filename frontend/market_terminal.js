(() => {
  const canvas = document.getElementById('price-chart');
  if (!canvas) return;
  const pair = document.getElementById('market-pair');
  const exchange = document.getElementById('market-exchange');
  const timeframe = document.getElementById('market-timeframe');
  if (!pair || !exchange || !timeframe) return;
  canvas.classList.add('market-chart');
  const wrapper = document.createElement('div'); wrapper.className = 'market-chart-wrap';
  canvas.parentNode.insertBefore(wrapper, canvas); wrapper.appendChild(canvas);
  const toolbar = document.createElement('div'); toolbar.className = 'market-chart-toolbar';
  toolbar.innerHTML = '<span class="chart-legend"><span class="legend-dot up"></span>Рост <span class="legend-dot down"></span>Падение</span><span id="chart-ohlc" class="chart-ohlc">—</span>';
  wrapper.parentNode.insertBefore(toolbar, wrapper);
  const tooltip = document.createElement('div'); tooltip.className = 'market-chart-tooltip'; tooltip.hidden = true; wrapper.appendChild(tooltip);
  let rows = [], dpr = 1, plot = {left: 12, right: 70, top: 12, bottom: 28, width: 0, height: 0};
  const css = name => getComputedStyle(document.body).getPropertyValue(name).trim();
  const colors = () => ({grid: css('--chart-grid') || '#d5dde5', text: css('--muted') || '#526b80', up: css('--chart-up') || '#16a34a', down: css('--chart-down') || '#dc2626', cross: css('--chart-cross') || '#718096'});
  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect(); dpr = Math.max(1, Math.min(devicePixelRatio || 1, 2));
    canvas.width = Math.max(320, Math.floor(rect.width * dpr)); canvas.height = Math.max(360, Math.floor(480 * dpr)); canvas.style.height = '480px';
    plot = {left: 10*dpr, right: 76*dpr, top: 14*dpr, bottom: 34*dpr, width: canvas.width-86*dpr, height: canvas.height-48*dpr}; draw();
  }
  function normalized() { return rows.map(item => ({timestamp:Number(item.timestamp), open:Number(item.open), high:Number(item.high), low:Number(item.low), close:Number(item.close), volume:Number(item.volume||0)})).filter(c => [c.timestamp,c.open,c.high,c.low,c.close].every(Number.isFinite) && c.high>=c.low && c.high>0 && c.low>0); }
  function draw() {
    const ctx = canvas.getContext('2d'); if (!ctx) return; ctx.clearRect(0,0,canvas.width,canvas.height); const data=normalized(); if(!data.length)return;
    const c=colors(), max=Math.max(...data.map(x=>x.high)), min=Math.min(...data.map(x=>x.low)), range=Math.max(max-min,Math.abs(max)*0.0001,1e-9), vmax=Math.max(...data.map(x=>x.volume),1), priceHeight=plot.height*.78, volumeTop=plot.top+priceHeight+8*dpr, volumeHeight=plot.height-priceHeight-8*dpr, visible=data.slice(-120), slot=plot.width/visible.length, body=Math.max(2*dpr,slot*.58), y=v=>plot.top+(max-v)/range*priceHeight;
    ctx.font=`${11*dpr}px system-ui,sans-serif`; ctx.textAlign='right'; ctx.textBaseline='middle'; ctx.strokeStyle=c.grid; ctx.fillStyle=c.text; ctx.lineWidth=dpr;
    for(let i=0;i<=6;i++){const yy=plot.top+(priceHeight/6)*i;ctx.beginPath();ctx.moveTo(plot.left,yy);ctx.lineTo(plot.left+plot.width,yy);ctx.stroke();ctx.fillText((max-(range/6)*i).toFixed(max>=100?2:4),canvas.width-8*dpr,yy);}
    for(let i=0;i<=4;i++){const xx=plot.left+plot.width*i/4;ctx.beginPath();ctx.moveTo(xx,plot.top);ctx.lineTo(xx,plot.top+plot.height);ctx.stroke();}
    visible.forEach((candle,i)=>{const x=plot.left+i*slot+slot/2, color=candle.close>=candle.open?c.up:c.down;ctx.strokeStyle=color;ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(x,y(candle.high));ctx.lineTo(x,y(candle.low));ctx.stroke();const top=y(Math.max(candle.open,candle.close)),height=Math.max(dpr,Math.abs(y(candle.open)-y(candle.close)));ctx.fillRect(x-body/2,top,body,height);if(candle.volume>0){const vh=candle.volume/vmax*volumeHeight;ctx.globalAlpha=.22;ctx.fillRect(x-body/2,volumeTop+volumeHeight-vh,body,vh);ctx.globalAlpha=1;}});
    ctx.strokeStyle=c.grid;ctx.beginPath();ctx.moveTo(plot.left,volumeTop);ctx.lineTo(plot.left+plot.width,volumeTop);ctx.stroke();ctx.fillStyle=c.text;ctx.textAlign='center';ctx.textBaseline='top';[0,.25,.5,.75,1].forEach(p=>{const index=Math.min(visible.length-1,Math.floor((visible.length-1)*p)),x=plot.left+index*slot+slot/2;ctx.fillText(new Date(visible[index].timestamp).toLocaleString('ru-RU',{day:'2-digit',hour:'2-digit',minute:'2-digit'}),x,canvas.height-24*dpr);});
    const last=data[data.length-1];ctx.setLineDash([4*dpr,4*dpr]);ctx.strokeStyle=c.cross;ctx.beginPath();ctx.moveTo(plot.left,y(last.close));ctx.lineTo(plot.left+plot.width,y(last.close));ctx.stroke();ctx.setLineDash([]);
  }
  function candleAt(clientX,clientY){const rect=canvas.getBoundingClientRect(),x=(clientX-rect.left)*dpr,yPos=(clientY-rect.top)*dpr,data=normalized().slice(-120);if(!data.length||x<plot.left||x>plot.left+plot.width||yPos<plot.top||yPos>plot.top+plot.height)return null;const slot=plot.width/data.length,index=Math.max(0,Math.min(data.length-1,Math.floor((x-plot.left)/slot)));return {candle:data[index]};}
  canvas.addEventListener('mousemove',event=>{const hit=candleAt(event.clientX,event.clientY);if(!hit){tooltip.hidden=true;return;}const c=hit.candle,date=new Date(c.timestamp).toLocaleString('ru-RU');document.getElementById('chart-ohlc').textContent=`O ${c.open} H ${c.high} L ${c.low} C ${c.close}`;tooltip.hidden=false;tooltip.innerHTML=`<strong>${date}</strong><br>O ${c.open} · H ${c.high} · L ${c.low} · C ${c.close}<br>Объём: ${c.volume.toLocaleString('ru-RU')}`;const rect=canvas.getBoundingClientRect();tooltip.style.left=`${Math.min(rect.width-180,Math.max(8,event.clientX-rect.left+12))}px`;tooltip.style.top=`${Math.max(8,event.clientY-rect.top+12)}px`;});
  canvas.addEventListener('mouseleave',()=>{tooltip.hidden=true;});
  async function refresh(){const url=`/api/market/history?pair=${encodeURIComponent(pair.value)}&exchange=${encodeURIComponent(exchange.value)}&timeframe=${encodeURIComponent(timeframe.value)}`;try{const response=await fetch(url,{headers:{Accept:'application/json'}}),data=await response.json();if(!response.ok)throw new Error(data.detail||'Не удалось загрузить историю свечей');rows=data.candles||[];resizeCanvas();const last=normalized().at(-1);if(last)document.getElementById('chart-ohlc').textContent=`O ${last.open} H ${last.high} L ${last.low} C ${last.close}`;}catch(error){const ticker=document.getElementById('ticker');if(ticker)ticker.textContent=error.message;}}
  pair.addEventListener('change',refresh);exchange.addEventListener('change',refresh);timeframe.addEventListener('change',refresh);window.addEventListener('resize',resizeCanvas,{passive:true});if(window.ResizeObserver)new ResizeObserver(resizeCanvas).observe(wrapper);refresh();setInterval(refresh,15000);
})();
