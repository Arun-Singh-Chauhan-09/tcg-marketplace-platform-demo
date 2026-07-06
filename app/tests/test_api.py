"""Smoke tests. CI provides MySQL + Redis as GitLab services (see .gitlab-ci.yml)."""
from fastapi.testclient import TestClient
import main


def test_healthz():
    client = TestClient(main.app)
    assert client.get("/healthz").json() == {"status": "ok"}
