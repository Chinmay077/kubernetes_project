"""
MiniMart Kubernetes Learning Lab - Backend API
Flask service providing product data backed by SQLite.

DB file lives at /data/minimart.db  (mounted via emptyDir in Kubernetes).
On first startup the schema is created and seeded automatically.
"""

import os
import time
import socket
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pod identity – injected via Kubernetes Downward API env vars
# ---------------------------------------------------------------------------
POD_NAME      = os.environ.get("POD_NAME",      socket.gethostname())
POD_NAMESPACE = os.environ.get("POD_NAMESPACE", "default")
APP_VERSION   = os.environ.get("APP_VERSION",   "1.0.0")
NODE_NAME     = os.environ.get("NODE_NAME",     "unknown-node")

# ---------------------------------------------------------------------------
# SQLite – DB lives in /data so a Kubernetes volume can be mounted there.
# Fallback: ./minimart.db  when running locally without the volume.
# ---------------------------------------------------------------------------
DB_DIR  = os.environ.get("DB_DIR", "/data")
DB_PATH = os.path.join(DB_DIR, "minimart.db")

SEED_PRODUCTS = [
    ("Wireless Headphones",  79.99,  "Electronics", 42, 4.5, "🎧"),
    ("Mechanical Keyboard",  129.99, "Electronics", 18, 4.7, "⌨️"),
    ("USB-C Hub",            39.99,  "Electronics", 65, 4.2, "🔌"),
    ("Standing Desk Mat",    49.99,  "Office",       30, 4.6, "🟩"),
    ("Ergonomic Mouse",      59.99,  "Electronics", 22, 4.4, "🖱️"),
    ("Monitor Light Bar",    35.99,  "Lighting",    55, 4.8, "💡"),
    ("Cable Management Kit", 19.99,  "Office",       80, 4.3, "🗂️"),
    ("Laptop Stand",         44.99,  "Office",       35, 4.5, "💻"),
    ("Webcam 1080p",         89.99,  "Electronics", 15, 4.1, "📷"),
    ("Desk Organiser",       29.99,  "Office",       50, 4.4, "🗄️"),
    ("Noise-Cancel Mic",     99.99,  "Electronics", 12, 4.6, "🎤"),
    ("Smart Plug 4-Pack",    24.99,  "Smart Home",  70, 4.3, "🔋"),
]


def init_db():
    """Create schema and seed data on first run."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL,
                price    REAL    NOT NULL,
                category TEXT    NOT NULL,
                stock    INTEGER DEFAULT 0,
                rating   REAL    DEFAULT 0.0,
                image    TEXT    DEFAULT '📦'
            )
        """)
        # Seed only when table is empty (first boot)
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO products (name, price, category, stock, rating, image) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                SEED_PRODUCTS,
            )
            logger.info("DB seeded with %d products at %s", len(SEED_PRODUCTS), DB_PATH)
        conn.commit()
    logger.info("SQLite DB ready | path=%s", DB_PATH)


@contextmanager
def get_db():
    """Yield a thread-local SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row):
    return dict(row)


# ---------------------------------------------------------------------------
# Counters / identity helpers
# ---------------------------------------------------------------------------
request_counter = 0
start_time = time.time()

# Initialize DB at module load (runs for both `python app.py` and gunicorn)
init_db()


def pod_meta():
    return {
        "pod_name":       POD_NAME,
        "pod_namespace":  POD_NAMESPACE,
        "node_name":      NODE_NAME,
        "app_version":    APP_VERSION,
        "uptime_seconds": round(time.time() - start_time, 1),
        "request_count":  request_counter,
    }


@app.before_request
def log_request():
    global request_counter
    request_counter += 1
    logger.info(
        "REQUEST #%d | %s %s | from %s | pod=%s",
        request_counter, request.method, request.path,
        request.remote_addr, POD_NAME,
    )


def json_response(data, status=200):
    payload = {
        "data": data,
        "meta": {
            **pod_meta(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service":   "minimart-backend",
        },
    }
    resp = jsonify(payload)
    resp.status_code = status
    resp.headers["X-Pod-Name"]    = POD_NAME
    resp.headers["X-App-Version"] = APP_VERSION
    return resp


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return json_response({"message": "MiniMart Backend API", "endpoints": [
        "/api/products", "/api/products/<id>", "/api/categories",
        "/api/info", "/api/db/stats", "/health", "/ready",
    ]})


# ── Products ─────────────────────────────────────────────────────────────────

@app.route("/api/products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    with get_db() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM products WHERE LOWER(category)=LOWER(?)", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products").fetchall()
    products = [row_to_dict(r) for r in rows]
    return json_response({"products": products, "total": len(products)})


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id=?", (product_id,)
        ).fetchone()
    if not row:
        return json_response({"error": "Product not found"}, 404)
    return json_response({"product": row_to_dict(row)})


@app.route("/api/products", methods=["POST"])
def create_product():
    body = request.get_json(silent=True) or {}
    name     = body.get("name")
    price    = body.get("price")
    category = body.get("category", "Uncategorised")
    stock    = body.get("stock", 0)
    rating   = body.get("rating", 0.0)
    image    = body.get("image", "📦")
    if not name or price is None:
        return json_response({"error": "name and price are required"}, 400)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO products (name, price, category, stock, rating, image) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, price, category, stock, rating, image),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM products WHERE id=?", (new_id,)).fetchone()
    logger.info("Product created | id=%d | name=%s | pod=%s", new_id, name, POD_NAME)
    return json_response({"product": row_to_dict(row)}, 201)


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    body = request.get_json(silent=True) or {}
    allowed = {"name", "price", "category", "stock", "rating", "image"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        return json_response({"error": "Nothing to update"}, 400)
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values     = list(updates.values()) + [product_id]
    with get_db() as conn:
        conn.execute(f"UPDATE products SET {set_clause} WHERE id=?", values)
        conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not row:
        return json_response({"error": "Product not found"}, 404)
    logger.info("Product updated | id=%d | pod=%s", product_id, POD_NAME)
    return json_response({"product": row_to_dict(row)})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            return json_response({"error": "Product not found"}, 404)
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
    logger.info("Product deleted | id=%d | pod=%s", product_id, POD_NAME)
    return json_response({"deleted": product_id})


# ── Categories ───────────────────────────────────────────────────────────────

@app.route("/api/categories")
def get_categories():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()
    categories = [r["category"] for r in rows]
    return json_response({"categories": categories})


# ── DB stats (learning endpoint) ─────────────────────────────────────────────

@app.route("/api/db/stats")
def db_stats():
    """Shows students the physical DB file and row count."""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    try:
        size_bytes = os.path.getsize(DB_PATH)
    except OSError:
        size_bytes = 0
    return json_response({
        "db_path":    DB_PATH,
        "db_size_kb": round(size_bytes / 1024, 2),
        "row_count":  count,
        "note": (
            "This SQLite file is stored in an emptyDir volume. "
            "Data survives pod restarts on the same node but is lost "
            "if the pod moves to a new node. Use a PVC for true persistence."
        ),
    })


# ── Info / Health / Ready ─────────────────────────────────────────────────────

@app.route("/api/info")
def api_info():
    return json_response({"pod": pod_meta(), "db_path": DB_PATH})


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "pod": POD_NAME, "version": APP_VERSION})


@app.route("/ready")
def ready():
    return jsonify({"status": "ready", "pod": POD_NAME, "version": APP_VERSION})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting MiniMart Backend | pod=%s | version=%s | port=%d",
                POD_NAME, APP_VERSION, port)
    app.run(host="0.0.0.0", port=port, debug=False)
