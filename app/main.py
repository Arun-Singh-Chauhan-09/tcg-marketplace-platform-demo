"""TCG marketplace demo API: card catalog (MySQL) + price lookups (Redis-cached).

Structured JSON logging to stdout (picked up by Promtail -> Loki).
Prometheus metrics at /metrics, incl. cache hit/miss counters.
"""

import json
import logging
import os
import sys
import time

import pymysql
import redis
from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, Histogram, make_asgi_app


# ---------- structured JSON logging ----------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": "tcg-marketplace",
        }
        if hasattr(record, "extra"):
            payload.update(record.extra)
        return json.dumps(payload)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger("tcg")
log.addHandler(handler)
log.setLevel(logging.INFO)

# ---------- metrics ----------
REQUESTS = Histogram(
    "http_request_duration_seconds", "Request latency", ["path", "method", "status"]
)
CACHE_HITS = Counter("price_cache_hits_total", "Redis price cache hits")
CACHE_MISSES = Counter("price_cache_misses_total", "Redis price cache misses")

PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "60"))

app = FastAPI(title="TCG Marketplace Demo")
app.mount("/metrics", make_asgi_app())


def db() -> pymysql.Connection:
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "mysql"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "test"),
        database=os.getenv("MYSQL_DATABASE", "cards"),
        cursorclass=pymysql.cursors.DictCursor,
    )


cache = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))


@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    REQUESTS.labels(request.url.path, request.method, response.status_code).observe(
        time.perf_counter() - start
    )
    log.info(
        "request",
        extra={
            "extra": {
                "path": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        },
    )
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        cache.ping()
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ready"}


@app.get("/cards/search")
def search(q: str, limit: int = 20):
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, game, rarity FROM cards WHERE name LIKE %s LIMIT %s",
            (f"%{q}%", min(limit, 100)),
        )
        return {"results": cur.fetchall()}


@app.get("/cards/{card_id}/price")
def price(card_id: int):
    key = f"price:{card_id}"
    cached = cache.get(key)
    if cached is not None:
        CACHE_HITS.inc()
        return json.loads(cached) | {"cache": "hit"}

    CACHE_MISSES.inc()
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT card_id, avg_price_eur, min_price_eur, offers FROM prices WHERE card_id=%s",
            (card_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="card not found")
    payload = {k: float(v) if k.endswith("_eur") else v for k, v in row.items()}
    cache.setex(key, PRICE_CACHE_TTL, json.dumps(payload))
    return payload | {"cache": "miss"}
