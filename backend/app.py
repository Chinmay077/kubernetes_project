"""
MiniMart Kubernetes Learning Lab - Backend API
Flask service providing product data and Kubernetes learning telemetry.
"""

import os
import time
import socket
import logging
from datetime import datetime, timezone
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the frontend pod/container

# Structured logging so students can read kubectl logs output clearly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pod identity – injected via Kubernetes Downward API env vars
# ---------------------------------------------------------------------------
POD_NAME = os.environ.get("POD_NAME", socket.gethostname())
POD_NAMESPACE = os.environ.get("POD_NAMESPACE", "default")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
NODE_NAME = os.environ.get("NODE_NAME", "unknown-node")

# ---------------------------------------------------------------------------
# In-memory product catalogue
# NOTE for students: This data lives only in RAM. If this Pod is deleted
# and a new one starts, the data resets. A real system would use a
# persistent database (e.g. PostgreSQL with a PersistentVolumeClaim).
# ---------------------------------------------------------------------------
PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones",  "price": 79.99,  "category": "Electronics", "stock": 42, "rating": 4.5, "image": "🎧"},
    {"id": 2, "name": "Mechanical Keyboard",  "price": 129.99, "category": "Electronics", "stock": 18, "rating": 4.7, "image": "⌨️"},
    {"id": 3, "name": "USB-C Hub",            "price": 39.99,  "category": "Electronics", "stock": 65, "rating": 4.2, "image": "🔌"},
    {"id": 4, "name": "Standing Desk Mat",    "price": 49.99,  "category": "Office",      "stock": 30, "rating": 4.6, "image": "🟩"},
    {"id": 5, "name": "Ergonomic Mouse",      "price": 59.99,  "category": "Electronics", "stock": 22, "rating": 4.4, "image": "🖱️"},
    {"id": 6, "name": "Monitor Light Bar",    "price": 35.99,  "category": "Lighting",    "stock": 55, "rating": 4.8, "image": "💡"},
    {"id": 7, "name": "Cable Management Kit", "price": 19.99,  "category": "Office",      "stock": 80, "rating": 4.3, "image": "🗂️"},
    {"id": 8, "name": "Laptop Stand",         "price": 44.99,  "category": "Office",      "stock": 35, "rating": 4.5, "image": "💻"},
    {"id": 9, "name": "Webcam 1080p",         "price": 89.99,  "category": "Electronics", "stock": 15, "rating": 4.1, "image": "📷"},
    {"id":10, "name": "Desk Organiser",       "price": 29.99,  "category": "Office",      "stock": 50, "rating": 4.4, "image": "🗄️"},
    {"id":11, "name": "Noise-Cancel Mic",     "price": 99.99,  "category": "Electronics", "stock": 12, "rating": 4.6, "image": "🎤"},
    {"id":12, "name": "Smart Plug 4-Pack",    "price": 24.99,  "category": "Smart Home",  "stock": 70, "rating": 4.3, "image": "🔋"},
]

# Simple in-memory request counter (per pod, resets on restart)
request_counter = 0
start_time = time.time()


def pod_meta():
    """Return a dictionary describing this specific Pod's identity."""
    return {
        "pod_name": POD_NAME,
        "pod_namespace": POD_NAMESPACE,
        "node_name": NODE_NAME,
        "app_version": APP_VERSION,
        "uptime_seconds": round(time.time() - start_time, 1),
        "request_count": request_counter,
    }


@app.before_request
def log_request():
    global request_counter
    request_counter += 1
    logger.info(
        "REQUEST #%d | %s %s | from %s | pod=%s",
        request_counter,
        request.method,
        request.path,
        request.remote_addr,
        POD_NAME,
    )


def json_response(data, status=200):
    """Wrap data with pod metadata and return a Flask Response."""
    payload = {
        "data": data,
        "meta": {
            **pod_meta(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "minimart-backend",
        },
    }
    resp = jsonify(payload)
    resp.status_code = status
    # Expose pod name as a response header so the frontend can display it
    resp.headers["X-Pod-Name"] = POD_NAME
    resp.headers["X-App-Version"] = APP_VERSION
    return resp


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return json_response({"message": "MiniMart Backend API", "endpoints": [
        "/api/products", "/api/products/<id>", "/health", "/ready", "/api/info"
    ]})


@app.route("/api/products")
def get_products():
    category = request.args.get("category")
    if category:
        filtered = [p for p in PRODUCTS if p["category"].lower() == category.lower()]
    else:
        filtered = PRODUCTS
    return json_response({"products": filtered, "total": len(filtered)})


@app.route("/api/products/<int:product_id>")
def get_product(product_id):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return json_response({"error": "Product not found"}, 404)
    return json_response({"product": product})


@app.route("/api/info")
def api_info():
    """Return pod identity and stats – used by the lab dashboard."""
    return json_response({
        "pod": pod_meta(),
        "note": (
            "In-memory data resets when this Pod restarts. "
            "This is intentional – it teaches Pod ephemerality."
        ),
    })


@app.route("/health")
def health():
    """Liveness probe endpoint. Returns 200 as long as the process runs."""
    return jsonify({"status": "healthy", "pod": POD_NAME, "version": APP_VERSION})


@app.route("/ready")
def ready():
    """
    Readiness probe endpoint.
    Returns 200 when the service is ready to accept traffic.
    Students can simulate a not-ready state by temporarily returning 503.
    """
    return jsonify({"status": "ready", "pod": POD_NAME, "version": APP_VERSION})


@app.route("/api/categories")
def get_categories():
    categories = sorted(set(p["category"] for p in PRODUCTS))
    return json_response({"categories": categories})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting MiniMart Backend | pod=%s | version=%s | port=%d",
                POD_NAME, APP_VERSION, port)
    app.run(host="0.0.0.0", port=port, debug=False)
