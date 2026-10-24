# ─── Stage 1: build ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=1.0.0 \
    PORT=6000

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app.py .

EXPOSE 6000

CMD ["gunicorn", "--bind", "0.0.0.0:6000", "--workers", "1", "--timeout", "60", "app:app"]
