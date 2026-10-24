"""
MiniMart Kubernetes Learning Lab – Frontend Service
Serves HTML pages and proxies API calls to the backend ClusterIP Service.

Why a proxy?
  The browser cannot directly reach the backend ClusterIP Service (it is
  internal to the cluster). The frontend pod, running inside the cluster,
  CAN reach it via Kubernetes DNS. So we proxy /api/proxy/* → backend:5000.
"""

import os
import socket
import logging
import requests
from flask import Flask, render_template, jsonify, request, Response, abort

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ── Identity ──────────────────────────────────────────────────────────────
POD_NAME    = os.environ.get("POD_NAME", socket.gethostname())
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

# Backend service DNS name – Kubernetes resolves this automatically when both
# Deployment + Service are in the same namespace.
# Students: change this only if you rename the backend Service.
BACKEND_URL       = os.environ.get("BACKEND_URL",       "http://minimart-backend-svc:5000")
NOTIFICATION_URL  = os.environ.get("NOTIFICATION_URL",  "http://minimart-notification-svc:6000")

logger.info("Frontend starting | pod=%s | backend=%s", POD_NAME, BACKEND_URL)


# ── Pages ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/lab")
def lab():
    return render_template("lab.html")


# ── Proxy ──────────────────────────────────────────────────────────────────
# Paths that go directly to the backend root (no /api/ prefix)
HEALTH_PATHS = {"health", "ready"}
ALLOWED_PROXY_PATHS = {"products", "info", "categories", "health", "ready", "db"}


def _proxy(path):
    """Forward a request to the backend and inject frontend pod identity."""
    base = path.split("/")[0]
    if base in HEALTH_PATHS:
        url = f"{BACKEND_URL}/{path}"
    else:
        url = f"{BACKEND_URL}/api/{path}"
    params = request.args.to_dict()
    try:
        logger.info("PROXY → %s | pod=%s", url, POD_NAME)
        if request.method == "POST":
            r = requests.post(url, json=request.get_json(silent=True), timeout=5)
        elif request.method == "PUT":
            r = requests.put(url, json=request.get_json(silent=True), timeout=5)
        elif request.method == "DELETE":
            r = requests.delete(url, timeout=5)
        else:
            r = requests.get(url, params=params, timeout=5)
        data = r.json()
        data["frontend_pod"]     = POD_NAME
        data["frontend_version"] = APP_VERSION
        resp = jsonify(data)
        resp.status_code = r.status_code
        resp.headers["X-Frontend-Pod"] = POD_NAME
        return resp
    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach backend at %s", url)
        return jsonify({
            "error": "Backend service unreachable",
            "backend_url": url,
            "hint": "Run: kubectl get svc minimart-backend-svc",
        }), 503
    except Exception as exc:
        logger.exception("Proxy error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/proxy/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    base = path.split("/")[0]
    if base not in ALLOWED_PROXY_PATHS:
        abort(404)
    return _proxy(path)


# ── Notification service proxy ──────────────────────────────────────────────
@app.route("/api/notify/<path:path>", methods=["GET", "DELETE"])
def notify_proxy(path):
    """Proxy to the notification-service so the browser can poll events."""
    url = f"{NOTIFICATION_URL}/{path}"
    try:
        if request.method == "DELETE":
            r = requests.delete(url, timeout=5)
        else:
            r = requests.get(url, timeout=5)
        data = r.json()
        data["frontend_pod"] = POD_NAME
        return jsonify(data), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Notification service unreachable",
                        "hint": "Run: kubectl get svc minimart-notification-svc"}), 503
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Health / Readiness probes (for the frontend pod itself) ──────────────
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "pod": POD_NAME, "version": APP_VERSION})


@app.route("/ready")
def ready():
    return jsonify({"status": "ready", "pod": POD_NAME, "version": APP_VERSION})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
