/**
 * MiniMart Shop – product loading and display logic
 * Fetches from /api/proxy/products (served by the frontend Flask app)
 * which internally calls the backend ClusterIP service.
 */

const API = '/api/proxy';
let allProducts = [];
let requestCount = 0;

// ── Utility ─────────────────────────────────────────────────────────────
function stars(rating) {
  const full  = Math.floor(rating);
  const half  = rating % 1 >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(empty);
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString();
}

// ── DOM helpers ──────────────────────────────────────────────────────────
function setInfo(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ── Product rendering ────────────────────────────────────────────────────
function renderProducts(products) {
  const grid = document.getElementById('productsGrid');
  if (!products.length) {
    grid.innerHTML = '<div class="error-state">No products found for this category.</div>';
    return;
  }
  grid.innerHTML = products.map(p => {
    const stockClass = p.stock < 20 ? 'stock-low' : '';
    return `
      <div class="product-card" onclick="addToCart(${p.id})">
        <div class="product-emoji">${p.image}</div>
        <div class="product-name">${p.name}</div>
        <div class="product-category">${p.category}</div>
        <div class="product-row">
          <span class="product-price">$${p.price.toFixed(2)}</span>
          <span class="product-rating">${stars(p.rating)} ${p.rating}</span>
        </div>
        <div class="product-stock ${stockClass}">
          ${p.stock < 20 ? '⚠️ Low stock: ' : '✓ In stock: '}${p.stock} units
        </div>
      </div>`;
  }).join('');
}

function renderCategories(categories) {
  const filter = document.getElementById('categoryFilter');
  const existing = filter.innerHTML; // keep "All" button
  categories.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'cat-btn';
    btn.textContent = cat;
    btn.onclick = () => filterCategory(cat, btn);
    filter.appendChild(btn);
  });
}

function filterCategory(cat, btn) {
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (cat) {
    renderProducts(allProducts.filter(p => p.category === cat));
  } else {
    renderProducts(allProducts);
  }
}

// ── Data loading ─────────────────────────────────────────────────────────
async function loadProducts() {
  const grid = document.getElementById('productsGrid');
  grid.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Fetching products from backend Pod…</p></div>';
  const btn = document.getElementById('refreshBtn');
  if (btn) btn.textContent = '↺ Loading…';

  const t0 = performance.now();
  try {
    const resp = await fetch(`${API}/products`);
    const latency = Math.round(performance.now() - t0);

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();

    // Update pod info from response
    const meta = json.meta || {};
    requestCount++;
    setInfo('fePodName',  json.frontend_pod  || 'serving');
    setInfo('bePodName',  meta.pod_name       || '–');
    setInfo('beVersion',  meta.app_version    || '–');
    setInfo('lastRequest', formatTime(meta.timestamp || new Date().toISOString()));
    setInfo('reqCount',   meta.request_count  || requestCount);

    // Navbar pill
    const pill = document.getElementById('frontendPod');
    if (pill) pill.textContent = '🖥 Pod: ' + (json.frontend_pod || 'frontend');
    const ver = document.getElementById('frontendVersion');
    if (ver) ver.textContent = 'v' + (json.frontend_version || '1.0.0');

    // Products
    const products = json.data?.products || [];
    allProducts = products;
    renderProducts(products);

    // Categories (only first load)
    if (document.querySelectorAll('.cat-btn').length <= 1) {
      try {
        const catResp = await fetch(`${API}/categories`);
        const catJson = await catResp.json();
        renderCategories(catJson.data?.categories || []);
      } catch (_) {}
    }

    if (btn) btn.textContent = '↺ Refresh';
  } catch (err) {
    grid.innerHTML = `
      <div class="error-state">
        <p>⚠️ Could not load products</p>
        <p style="font-size:12px;margin-top:8px;">${err.message}</p>
        <p style="font-size:12px;margin-top:6px;color:#7d8590;">
          Make sure the backend Service is reachable.<br>
          Run: <code>kubectl get pods,svc</code>
        </p>
      </div>`;
    if (btn) btn.textContent = '↺ Retry';
  }
}

function addToCart(id) {
  // Intentionally simple – teaches that state is in the browser, not a pod
  const p = allProducts.find(x => x.id === id);
  if (p) {
    const msg = document.createElement('div');
    msg.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#3fb95022;border:1px solid #3fb950;color:#3fb950;padding:10px 18px;border-radius:8px;font-size:13px;z-index:9999;transition:opacity .5s';
    msg.textContent = `✓ ${p.name} added to cart`;
    document.body.appendChild(msg);
    setTimeout(() => { msg.style.opacity = '0'; setTimeout(() => msg.remove(), 500); }, 2000);
  }
}

// ── Init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadProducts);
