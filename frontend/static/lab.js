/**
 * MiniMart K8s Lab Dashboard – interactive lab logic
 *
 * Data sourcing policy (strictly followed):
 *  🟢 LIVE  – data comes from actual HTTP responses to /api/proxy/*
 *  🟡 SIM   – illustrative animations not backed by real cluster events
 */

'use strict';

const Lab = (() => {
  // ── State ──────────────────────────────────────────────────────
  let totalRequests  = 0;
  const fePodsMap    = {};   // podName → hit count
  const bePodsMap    = {};
  const logRows      = [];
  let simPodCount    = 3;    // for scaling sim
  let healPods       = [];   // for self-heal sim

  // ── DOM helpers ───────────────────────────────────────────────
  const $  = id => document.getElementById(id);
  const set = (id, v) => { const el=$(id); if(el) el.textContent=v; };

  // ── Request flow ──────────────────────────────────────────────
  async function sendRequest() {
    totalRequests++;
    const t0 = performance.now();

    // Animate packets through the diagram
    animateFlow();

    try {
      const resp = await fetch('/api/proxy/products');
      const latency = Math.round(performance.now() - t0);
      const json = await resp.json();

      const fePod = json.frontend_pod || '(frontend)';
      const meta  = json.meta || {};
      const bePod = meta.pod_name || '(backend)';
      const beVer = meta.app_version || '1.0.0';

      // Update maps
      fePodsMap[fePod] = (fePodsMap[fePod] || 0) + 1;
      bePodsMap[bePod] = (bePodsMap[bePod] || 0) + 1;

      // Update stats bar
      set('totalRequests', totalRequests);
      set('lastFePod', shorten(fePod));
      set('lastBePod', shorten(bePod));
      set('uniqueFe', Object.keys(fePodsMap).length);
      set('uniqueBe', Object.keys(bePodsMap).length);

      // Update pod cards
      updatePodCards('fePods', fePodsMap, fePod, 'Frontend', beVer);
      updatePodCards('bePods', bePodsMap, bePod, 'Backend',  beVer);

      // Log table
      appendLog(fePod, bePod, resp.status, latency);

      // Update LB chart
      updateLbChart();
    } catch(err) {
      appendLog('error', 'error', 0, 0, err.message);
    }
  }

  async function sendBurst(n = 10) {
    for (let i = 0; i < n; i++) {
      await sendRequest();
      await sleep(120);
    }
  }

  async function refresh() {
    await loadArchData();
    await sendRequest();
  }

  // ── Architecture data (from live API) ─────────────────────────
  async function loadArchData() {
    try {
      const r = await fetch('/api/proxy/info');
      const j = await r.json();
      const meta = j.meta || {};
      // Update backend pod display
      const bePod = meta.pod_name || 'minimart-backend-xxx';
      if (!bePodsMap[bePod]) bePodsMap[bePod] = 0;
      updatePodCards('bePods', bePodsMap, bePod, 'Backend', meta.app_version||'1.0.0');
    } catch(_) {}
  }

  // ── Pod card rendering ─────────────────────────────────────────
  function updatePodCards(containerId, podMap, activePod, type, version) {
    const container = $(containerId);
    if (!container) return;

    container.innerHTML = '';
    const pods = Object.keys(podMap);

    // Always show at least 1 pod (the live one)
    const allPods = new Set(pods);
    allPods.add(activePod);

    allPods.forEach(name => {
      const isActive = (name === activePod);
      const count    = podMap[name] || 0;
      const div = document.createElement('div');
      div.className = 'pod-card' + (isActive ? ' active-pod' : '');
      div.innerHTML = `
        <div class="pod-status running">● Running</div>
        <div class="pod-name">${name}</div>
        <div class="pod-type">${type}</div>
        <div class="pod-version">${version}</div>
        <div class="pod-req-count">Hits: ${count}</div>
        <div class="container-box">
          <div class="container-icon">${type==='Frontend'?'🌐':'🐍'}</div>
          <div>${type==='Frontend'?'nginx/flask':'gunicorn'}</div>
        </div>`;
      container.appendChild(div);
    });
  }

  // ── Packet animation ───────────────────────────────────────────
  function animateFlow() {
    ['pkt1','pkt2','pkt3','pkt4'].forEach((id, i) => {
      setTimeout(() => {
        const el = $(id);
        if (!el) return;
        el.classList.remove('animating');
        void el.offsetWidth; // reflow
        el.classList.add('animating');
      }, i * 200);
    });
  }

  // ── Log table ──────────────────────────────────────────────────
  function appendLog(fePod, bePod, status, latency, err='') {
    const body = $('logBody');
    if (!body) return;

    // Remove empty placeholder
    const empty = body.querySelector('.empty-row');
    if (empty) empty.parentElement.remove();

    const tr = document.createElement('tr');
    tr.className = 'new-row';
    const statusClass = status >= 200 && status < 300 ? 'status-ok' : 'status-err';
    const now = new Date().toLocaleTimeString();
    tr.innerHTML = `
      <td>${totalRequests}</td>
      <td>${now}</td>
      <td><code>${shorten(fePod)}</code></td>
      <td><code>${shorten(bePod)}</code></td>
      <td class="${statusClass}">${status || 'ERR'}</td>
      <td>${latency}ms</td>`;
    body.prepend(tr);

    // Keep max 50 rows
    while (body.children.length > 50) body.removeChild(body.lastChild);
  }

  // ── LB chart ──────────────────────────────────────────────────
  function updateLbChart() {
    renderBars('fePodBars', fePodsMap, 'FE');
    renderBars('bePodBars', bePodsMap, 'BE');
  }

  function renderBars(containerId, map, prefix) {
    const container = $(containerId);
    if (!container) return;
    const max = Math.max(...Object.values(map), 1);
    container.innerHTML = Object.entries(map).map(([name, count]) => `
      <div class="bar-row">
        <span class="bar-label">${prefix}: ${shorten(name, 14)}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:${Math.round(count/max*100)}%"></div>
        </div>
        <span class="bar-count">${count}</span>
      </div>`).join('');
  }

  // ── Health check ──────────────────────────────────────────────
  async function checkHealth() {
    [['healthStatus','healthDetail','/api/proxy/health'],
     ['readyStatus', 'readyDetail', '/api/proxy/ready']].forEach(async ([sid, did, path]) => {
      const s = $(sid); const d = $(did);
      if(s) { s.textContent='Checking…'; s.className='health-status'; }
      try {
        const t0 = performance.now();
        const r = await fetch(path);
        const ms = Math.round(performance.now()-t0);
        const j = await r.json();
        if(s) { s.textContent = r.ok ? '✓ '+j.status : '✗ '+r.status; s.className='health-status '+(r.ok?'ok':'err'); }
        if(d) d.textContent = `pod: ${j.pod || '–'} | ${ms}ms`;
      } catch(e) {
        if(s) { s.textContent='✗ unreachable'; s.className='health-status err'; }
        if(d) d.textContent=e.message;
      }
    });
  }

  // ── Experiments toggle ─────────────────────────────────────────
  function toggleExp(id) {
    const body = $(id);
    const tog  = $(id+'Toggle');
    if (!body) return;
    const open = body.classList.toggle('open');
    if (tog) tog.classList.toggle('open', open);
  }

  // ── Routing demo ───────────────────────────────────────────────
  async function runRoutingDemo() {
    const results = $('routingResults');
    if (results) results.innerHTML = '';
    for (let i = 1; i <= 5; i++) {
      await sleep(300);
      try {
        const r = await fetch('/api/proxy/products');
        const j = await r.json();
        const fe = j.frontend_pod || 'frontend';
        const be = j.meta?.pod_name || 'backend';
        if (results) {
          const row = document.createElement('div');
          row.className = 'routing-row';
          row.textContent = `Request ${i} → FE: ${shorten(fe)} → BE: ${shorten(be)}`;
          results.appendChild(row);
        }
        fePodsMap[fe] = (fePodsMap[fe]||0)+1;
        bePodsMap[be] = (bePodsMap[be]||0)+1;
        totalRequests++;
      } catch(e) {
        if (results) {
          const row = document.createElement('div');
          row.className = 'routing-row';
          row.textContent = `Request ${i} → Error: ${e.message}`;
          results.appendChild(row);
        }
      }
    }
  }

  // ── Scaling simulator (🟡 SIM) ────────────────────────────────
  function renderSimPods(container, count, statusFn) {
    if (!container) return;
    container.innerHTML = '';
    for (let i = 1; i <= count; i++) {
      const st = statusFn ? statusFn(i) : 'running';
      const div = document.createElement('div');
      div.className = `sim-pod ${st}`;
      div.innerHTML = `<div class="sim-pod-icon">📦</div><div>Pod-${i}</div><div>${st}</div>`;
      container.appendChild(div);
    }
  }

  function simScale(n) {
    const container = $('simPods');
    if (n > simPodCount) {
      // Show existing pods + pending new ones
      renderSimPods(container, simPodCount, () => 'running');
      setTimeout(() => {
        renderSimPods(container, n, i => i <= simPodCount ? 'running' : 'pending');
        setTimeout(() => renderSimPods(container, n, () => 'running'), 1200);
      }, 300);
    } else if (n < simPodCount) {
      renderSimPods(container, simPodCount, i => i <= n ? 'running' : 'dead');
      setTimeout(() => renderSimPods(container, n, () => 'running'), 800);
    }
    simPodCount = n;
  }

  // ── Self-heal simulator (🟡 SIM) ──────────────────────────────
  function renderHealPods(statuses) {
    const container = $('healPods');
    if (!container) return;
    container.innerHTML = '';
    statuses.forEach((st, i) => {
      const div = document.createElement('div');
      div.className = `sim-pod ${st}`;
      div.innerHTML = `<div class="sim-pod-icon">${st==='dead'?'💀':'📦'}</div><div>Pod-${i+1}</div><div>${st}</div>`;
      container.appendChild(div);
    });
  }

  function initHealPods() {
    healPods = ['running','running','running'];
    renderHealPods(healPods);
  }

  function simDelete() {
    // Pick a random running pod
    const idx = healPods.findIndex(s => s === 'running');
    if (idx < 0) { initHealPods(); return; }
    healPods[idx] = 'dead';
    renderHealPods(healPods);
    setTimeout(() => {
      healPods[idx] = 'pending';
      renderHealPods(healPods);
      setTimeout(() => {
        healPods[idx] = 'running';
        renderHealPods(healPods);
      }, 1500);
    }, 800);
  }

  // ── Async Messaging (Experiment F) ────────────────────────────
  let _testProductCount = 0;

  async function createTestProduct() {
    _testProductCount++;
    const name = `Lab Product #${_testProductCount}`;
    const log  = $('notificationLog');
    if (log) {
      const row = document.createElement('div');
      row.className = 'routing-row';
      row.style.color = '#f59e0b';
      row.textContent = `⏳ Creating "${name}" via POST /api/proxy/products …`;
      log.prepend(row);
    }
    try {
      const t0 = performance.now();
      const r = await fetch('/api/proxy/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, price: 9.99, category: 'Demo', stock: 1 }),
      });
      const ms = Math.round(performance.now() - t0);
      const j  = await r.json();
      const id = j?.data?.product?.id || '?';
      if (log) {
        const row = document.createElement('div');
        row.className = 'routing-row';
        row.style.color = '#4ade80';
        row.textContent = `✓ Product id=${id} created in ${ms}ms — event fired async to notification-svc`;
        log.prepend(row);
      }
      // Auto-poll events after short delay (async arrives slightly later)
      setTimeout(refreshNotifications, 600);
    } catch(e) {
      if (log) {
        const row = document.createElement('div');
        row.className = 'routing-row';
        row.style.color = '#f87171';
        row.textContent = `✗ Error: ${e.message}`;
        log.prepend(row);
      }
    }
  }

  async function refreshNotifications() {
    const log = $('notificationLog');
    try {
      const r = await fetch('/api/notify/events');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      const events = j.events || [];
      if (!log) return;
      if (events.length === 0) {
        const row = document.createElement('div');
        row.className = 'routing-row';
        row.textContent = 'No events yet — create a product first.';
        log.innerHTML = '';
        log.appendChild(row);
        return;
      }
      log.innerHTML = '';
      events.slice(0, 20).forEach(ev => {
        const row = document.createElement('div');
        row.className = 'routing-row';
        const typeColor = ev.type === 'PRODUCT_CREATED' ? '#4ade80'
                       : ev.type === 'PRODUCT_DELETED'  ? '#f87171'
                       : '#f59e0b';
        row.innerHTML = `<span style="color:${typeColor};font-weight:600">${ev.type}</span> `
          + `&nbsp;id=${ev.id} &nbsp;from: ${shorten(ev.source)} &nbsp;`
          + `<span style="opacity:0.5">${new Date(ev.received_at).toLocaleTimeString()}</span>`;
        log.appendChild(row);
      });
    } catch(e) {
      if (log) {
        log.innerHTML = `<div class="routing-row" style="color:#f87171">
          Notification service unreachable — is it deployed? (${e.message})</div>`;
      }
    }
  }

  async function clearNotifications() {
    await fetch('/api/notify/events/clear', { method: 'DELETE' });
    const log = $('notificationLog');
    if (log) log.innerHTML = '<div class="routing-row" style="opacity:0.5">Queue cleared.</div>';
  }

  // ── Protocol Latency Comparison (Experiment G) ─────────────────
  async function runLatencyComparison() {
    const results = $('latencyResults');
    if (results) results.innerHTML = '<div class="routing-row" style="opacity:0.6">Running 5 rounds…</div>';

    for (let i = 1; i <= 5; i++) {
      await sleep(250);
      const t1 = performance.now();
      let restMs = 0, asyncMs = 0;
      try {
        await fetch('/api/proxy/products');
        restMs = Math.round(performance.now() - t1);
      } catch(_) { restMs = -1; }

      const t2 = performance.now();
      try {
        await fetch('/api/notify/events');
        asyncMs = Math.round(performance.now() - t2);
      } catch(_) { asyncMs = -1; }

      if (results) {
        const row = document.createElement('div');
        row.className = 'routing-row';
        const restColor  = restMs  < asyncMs ? '#4ade80' : '#f87171';
        const asyncColor = asyncMs < restMs  ? '#4ade80' : '#f59e0b';
        row.innerHTML = `Round ${i}: `
          + `<span style="color:${restColor}">REST /products → ${restMs}ms</span> &nbsp;|&nbsp; `
          + `<span style="color:${asyncColor}">Events poll → ${asyncMs}ms</span>`;
        if (i === 1 && results.children.length === 1) results.innerHTML = '';
        results.appendChild(row);
      }
    }
    if (results) {
      const note = document.createElement('div');
      note.style.cssText = 'opacity:0.5;font-size:0.78rem;margin-top:6px;padding:4px 0;border-top:1px solid rgba(255,255,255,0.1)';
      note.textContent = 'Larger payloads = more bytes = higher latency. gRPC binary encoding reduces this by ~60–80%.';
      results.appendChild(note);
    }
  }

  // ── Helpers ────────────────────────────────────────────────────
  function shorten(name, max=18) {
    if (!name) return '–';
    if (name.length <= max) return name;
    return name.slice(0, 6) + '…' + name.slice(-6);
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ── Init ───────────────────────────────────────────────────────
  function init() {
    loadArchData();
    checkHealth();
    // initialise sims
    renderSimPods($('simPods'), 3, () => 'running');
    initHealPods();
  }

  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return { sendRequest, sendBurst, refresh, toggleExp, runRoutingDemo,
           simScale, simDelete, checkHealth,
           createTestProduct, refreshNotifications, clearNotifications,
           runLatencyComparison };
})();
