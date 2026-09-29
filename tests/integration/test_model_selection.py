import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_workplace_example_and_explicit_model_requests(tmp_path, monkeypatch):
    monkeypatch.setenv("WEEKLY_JOBS", "false")
    # Legacy server variables must never implicitly select a model.
    monkeypatch.setenv("AI_RUNTIME", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "legacy-model")
    app = create_app(tmp_path / "work.db", False)
    with TestClient(app) as client:
        assert client.get("/api/v1/overview").status_code == 404
        assert client.get("/api/v1/batches").json()["items"] == []
        payload = Path("apps/web/public/templates/workplace-example.jsonl").read_bytes()
        response = client.post(
            "/api/v1/commands/import",
            files={"file": ("work.jsonl", payload, "application/x-ndjson")},
            headers={"Idempotency-Key": "workplace-1"},
        )
        assert response.json()["accepted"] == 10
        assert (
            client.post(
                "/api/v1/commands/analyze", json={}, headers={"Idempotency-Key": "workplace-analysis-1"}
            ).status_code
            == 200
        )
        position = client.get("/api/v1/evidence/example-crew/example-sku").json()
        assert position["position"]["expected"] == 26
        assert position["position"]["variance"] == -2
        assert position["position"]["days_of_supply"] is None  # Two counts do not make a forecast.
        alert = position["alerts"][0]
        path = "/api/v1/commands/explain/" + alert["id"]
        calls = []

        def generate(runtime, evidence, schema):
            calls.append(runtime.model)
            raise RuntimeError("chosen model unavailable")

        monkeypatch.setattr("consignai.ai.explain.OllamaRuntime.generate", generate)
        before = client.get("/api/v1/overview").json()
        for kwargs in ({}, {"json": {}}, {"json": {"model": None}}):
            result = client.post(path, **kwargs).json()
            assert result["mode"] == "deterministic"
            assert result["telemetry"]["model"] is None
        assert calls == []
        result = client.post(path, json={"model": "user-choice:small"}).json()
        assert result["mode"] == "deterministic_fallback"
        assert result["telemetry"]["model"] == "user-choice:small"
        assert calls == ["user-choice:small"]
        assert client.get("/api/v1/overview").json() == before
        assert client.post(path, json={"model": ""}).status_code == 422
        assert client.post(path, json={"model": "any", "base_url": "http://evil.test"}).status_code == 422
        assert all(
            json.loads(r["payload"])["tool_calls"] == []
            for r in app.state.store.query("SELECT payload FROM telemetry")
        )


def test_model_discovery_requires_read_permission(tmp_path, monkeypatch):
    monkeypatch.setenv("WEEKLY_JOBS", "false")
    monkeypatch.setenv("APP_MODE", "secured")
    monkeypatch.setenv("READ_API_KEY", "r" * 32)
    monkeypatch.setenv("WRITE_API_KEY", "w" * 32)
    monkeypatch.setattr(
        "apps.api.main.discover_models",
        lambda url: {"status": "empty", "models": [], "excluded_count": 0, "message": "No models installed"},
    )
    with TestClient(create_app(tmp_path / "secure.db", False)) as client:
        assert client.get("/api/v1/ai/models").status_code == 401
        response = client.get("/api/v1/ai/models", headers={"Authorization": "Bearer " + "r" * 32})
        assert response.status_code == 200
        assert response.json()["models"] == []
