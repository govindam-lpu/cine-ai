"""GET /health returns 200 with the expected shape."""


def test_health_returns_ok_and_version(client):
    resp = client.get("/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
