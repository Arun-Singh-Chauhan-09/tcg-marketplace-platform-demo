"""API tests for the TCG marketplace demo.

CI provides MySQL + Redis as services (see .gitlab-ci.yml). These tests exercise
the real cache path: a price lookup is a MISS first, then a HIT from Redis.
"""

import time

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="module")
def client():
    # Wait briefly for MySQL/Redis services to accept connections in CI.
    deadline = time.time() + 30
    last_err = None
    while time.time() < deadline:
        try:
            main.cache.ping()
            with main.db() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
            break
        except Exception as exc:  # pragma: no cover - startup race only
            last_err = exc
            time.sleep(1)
    else:  # pragma: no cover
        pytest.skip(f"backends not ready: {last_err}")

    _seed()
    return TestClient(main.app)


def _seed():
    ddl = [
        """CREATE TABLE IF NOT EXISTS cards (
             id INT AUTO_INCREMENT PRIMARY KEY,
             name VARCHAR(255) NOT NULL,
             game VARCHAR(16) NOT NULL,
             rarity VARCHAR(32),
             INDEX idx_name (name))""",
        """CREATE TABLE IF NOT EXISTS prices (
             card_id INT PRIMARY KEY,
             avg_price_eur DECIMAL(10,2),
             min_price_eur DECIMAL(10,2),
             offers INT)""",
    ]
    with main.db() as conn, conn.cursor() as cur:
        for stmt in ddl:
            cur.execute(stmt)
        cur.execute("SELECT COUNT(*) AS n FROM cards")
        if cur.fetchone()["n"] == 0:
            cur.execute(
                "INSERT INTO cards (id, name, game, rarity) VALUES "
                "(1,'Charizard Base Set','pokemon','holo rare')"
            )
            cur.execute("INSERT INTO prices VALUES (1, 320.50, 189.00, 412)")
        conn.commit()


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_search_finds_card(client):
    body = client.get("/cards/search", params={"q": "charizard"}).json()
    assert any("Charizard" in r["name"] for r in body["results"])


def test_search_empty(client):
    body = client.get("/cards/search", params={"q": "nonexistent-xyz"}).json()
    assert body["results"] == []


def test_price_miss_then_hit(client):
    main.cache.delete("price:1")

    first = client.get("/cards/1/price").json()
    assert first["cache"] == "miss"
    assert first["avg_price_eur"] == 320.5

    second = client.get("/cards/1/price").json()
    assert second["cache"] == "hit"
    assert second["avg_price_eur"] == 320.5


def test_price_not_found(client):
    assert client.get("/cards/999999/price").status_code == 404