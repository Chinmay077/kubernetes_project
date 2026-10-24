"""
MiniMart – Notification Service (Async Messaging Demo)
=======================================================
Teaching goal:
  Show students the difference between synchronous REST and
  asynchronous event-driven communication between microservices.

How it works:
  1. Backend POSTs a JSON event to THIS service at /events   (fire-and-forget)
  2. This service appends it to an in-memory queue (max 50)
  3. Frontend polls GET /events to display the notification log

Why this is realistic:
  In production you'd replace the HTTP POST with SQS/RabbitMQ/Kafka.
  The notification-service would be a separate consumer process.
  The pattern (producer → queue → consumer) stays identical.
"""

import os
import socket
import logging
from datetime import datetime, timezone
from collections import deque
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

POD_NAME    = os.environ.get("POD_NAME",    socket.gethostname())
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

# In-memory event queue — acts like a simplified message queue
# In production: replace with SQS, RabbitMQ, or Kafka consumer
EVENT_QUEUE: deque = deque(maxlen=50)


@app.route("/events", methods=["POST"])
def receive_event():
    """
    Producer endpoint – backend calls this fire-and-forget style.
    Backend does NOT wait for processing; it just drops the message here.
    This is the core of async communication.
    """
    body = request.get_json(silent=True) or {}
    event = {
        "id":        len(EVENT_QUEUE) + 1,
        "type":      body.get("type", "UNKNOWN"),
        "payload":   body.get("payload", {}),
        "source":    body.get("source", "unknown-pod"),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "processed_by": POD_NAME,
    }
    EVENT_QUEUE.appendleft(event)
    logger.info("Event received | type=%s | from=%s", event["type"], event["source"])

    # Simulate async processing (log only — no blocking work)
    _process_event(event)

    return jsonify({"status": "queued", "event_id": event["id"]}), 202  # 202 Accepted


def _process_event(event):
    """Simulate background processing — in production this runs in a worker thread/process."""
    etype = event["type"]
    if etype == "PRODUCT_CREATED":
        logger.info("[ASYNC] New product alert: %s", event["payload"].get("name"))
    elif etype == "STOCK_UPDATED":
        logger.info("[ASYNC] Stock change: product_id=%s new_stock=%s",
                    event["payload"].get("id"), event["payload"].get("stock"))
    elif etype == "PRODUCT_DELETED":
        logger.info("[ASYNC] Product removed: id=%s", event["payload"].get("id"))


@app.route("/events", methods=["GET"])
def get_events():
    """Consumer endpoint – frontend polls this to show the notification log."""
    return jsonify({
        "events":        list(EVENT_QUEUE),
        "total":         len(EVENT_QUEUE),
        "queue_type":    "in-memory (deque) — upgrade to SQS/RabbitMQ for production",
        "processor_pod": POD_NAME,
    })


@app.route("/events/clear", methods=["DELETE"])
def clear_events():
    EVENT_QUEUE.clear()
    return jsonify({"status": "cleared"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "pod": POD_NAME, "version": APP_VERSION,
                    "queue_depth": len(EVENT_QUEUE)})


@app.route("/")
def index():
    return jsonify({
        "service": "minimart-notification",
        "description": "Async event consumer — demonstrates fire-and-forget messaging",
        "endpoints": [
            "POST /events  — receive event from producer (backend)",
            "GET  /events  — list all queued events (polled by frontend)",
            "DELETE /events/clear — flush the queue",
            "GET  /health  — health probe",
        ],
        "pattern": "Producer (backend) → HTTP POST → Queue (this service) → Consumer (frontend poll)",
        "production_equivalent": "Producer → SQS/RabbitMQ/Kafka → Consumer worker",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6000))
    logger.info("Notification Service starting | pod=%s | port=%d", POD_NAME, port)
    app.run(host="0.0.0.0", port=port, debug=False)
