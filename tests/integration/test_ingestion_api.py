import json
from copy import deepcopy

import pytest
from consignai.data.store import Store
from consignai.services.ingestion import ingest
from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_atomic_rejection_and_visible_report(tmp_path, tiny_records):
    store = Store(tmp_path / "atomic.db")
    broken = deepcopy(tiny_records)
    broken[-1]["on_hand"] = -10
    result = ingest(store, broken, "../../malformed.jsonl")
    assert result["status"] == "rejected" and result["accepted"] == 0
    assert store.query("SELECT COUNT(*) n FROM records")[0]["n"] == 0
    assert len(store.query("SELECT * FROM batches")) == 1
    assert result["filename"] == "malformed.jsonl"
    assert result["errors"][0]["raw"]["on_hand"] == -10


def test_duplicate_and_conflicting_ids(tmp_path, tiny_records):
    store = Store(tmp_path / "dupes.db")
    assert ingest(store, tiny_records)["accepted"] == len(tiny_records)
    assert ingest(store, tiny_records)["duplicates"] == len(tiny_records)
    changed = deepcopy(tiny_records[0])
    changed["name"] = "conflicting"
    assert ingest(store, [changed])["status"] == "rejected"
    assert store.version() == "1"


def test_foreign_key_rejected(tmp_path, tiny_records):
    store = Store(tmp_path / "fk.db")
    movement = next(r for r in tiny_records if r["record_type"] == "movement")
    assert ingest(store, [movement])["status"] == "rejected"


def test_primary_api_workflow(tmp_path, tiny_records, monkeypatch):
    monkeypatch.setenv("WEEKLY_JOBS", "false")
    app = create_app(tmp_path / "api.db", False)
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/api/v1/overview").status_code == 404
        payload = "\n".join(json.dumps(r) for r in tiny_records)
        response = client.post(
            "/api/v1/commands/import",
            files={"file": ("demo.jsonl", payload, "application/x-ndjson")},
            headers={"Idempotency-Key": "import-1"},
        )
        assert response.status_code == 200 and response.json()["status"] == "accepted"
        same = client.post(
            "/api/v1/commands/import",
            files={"file": ("demo.jsonl", payload, "application/x-ndjson")},
            headers={"Idempotency-Key": "import-1"},
        )
        assert same.json() == response.json()
        headers = {"Idempotency-Key": "analysis-1"}
        run = client.post("/api/v1/commands/analyze", json={}, headers=headers)
        assert run.status_code == 200
        assert run.json() == client.post("/api/v1/commands/analyze", json={}, headers=headers).json()
        assert (
            client.post("/api/v1/commands/analyze", json={"as_of": "2025-01-15"}, headers=headers).status_code
            == 409
        )
        assert client.get("/api/v1/positions?limit=2").json()["limit"] == 2
        assert client.get("/api/v1/positions?limit=999").status_code == 422
        overview = client.get("/api/v1/overview")
        assert overview.headers["x-trace-id"]
        pos = client.get("/api/v1/positions").json()["items"][0]
        ev = client.get(f"/api/v1/evidence/{pos['location_id']}/{pos['sku']}").json()
        assert ev["snapshots"] and ev["movements"]
        assert client.get("/api/v1/export/exceptions.csv").headers["content-type"].startswith("text/csv")
        assert client.get("/openapi.json").status_code == 200


def test_import_errors_and_readonly_boundaries(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "secured")
    monkeypatch.setenv("READ_API_KEY", "r" * 32)
    monkeypatch.setenv("WRITE_API_KEY", "w" * 32)
    monkeypatch.setenv("WEEKLY_JOBS", "false")
    with TestClient(create_app(tmp_path / "secure.db", False)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/meta").status_code == 401
        assert client.get("/api/v1/meta", headers={"Authorization": "Bearer " + "r" * 32}).status_code == 200
        assert (
            client.post(
                "/api/v1/commands/analyze", json={}, headers={"Authorization": "Bearer " + "r" * 32}
            ).status_code
            == 401
        )
        key = {"X-API-Key": "w" * 32, "Idempotency-Key": "bad-upload"}
        assert (
            client.post(
                "/api/v1/commands/import",
                files={"file": ("bad.exe", b"x", "application/octet-stream")},
                headers=key,
            ).status_code
            == 415
        )
        result = client.post(
            "/api/v1/commands/import",
            files={"file": ("bad.jsonl", "{broken", "application/x-ndjson")},
            headers=key,
        )
        assert result.json()["status"] == "rejected"
        assert (
            client.get("/api/v1/batches", headers={"Authorization": "Bearer " + "r" * 32}).json()["total"]
            == 1
        )


def test_secure_startup_fails_without_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "secured")
    monkeypatch.delenv("WRITE_API_KEY", raising=False)
    monkeypatch.delenv("READ_API_KEY", raising=False)
    with pytest.raises(ValueError):
        create_app(tmp_path / "fail.db", False)


def test_sql_search_is_data(store, monkeypatch):
    monkeypatch.setenv("WEEKLY_JOBS", "false")
    with TestClient(create_app(store.path, False)) as client:
        assert client.get("/api/v1/positions", params={"q": "'; DROP TABLE records; --"}).status_code == 200
        assert store.query("SELECT COUNT(*) n FROM records")[0]["n"] > 0


def test_browser_origin_and_request_size(tmp_path, monkeypatch):
    monkeypatch.setenv("WEEKLY_JOBS", "false")
    with TestClient(create_app(tmp_path / "limits.db", False)) as client:
        assert (
            client.post(
                "/api/v1/commands/analyze", json={}, headers={"Origin": "https://attacker.invalid"}
            ).status_code
            == 403
        )
        response = client.post(
            "/api/v1/commands/import",
            content=b"x" * (21 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "body_too_large"


def test_malformed_csv_and_utf8_retained(tmp_path):
    from consignai.services.ingestion import decode_upload

    store = Store(tmp_path / "malformed.db")
    for content, name in [(b"\xff\xfe", "bad.jsonl"), (b"record_type,lineage\nsnapshot,not-json", "bad.csv")]:
        report = ingest(store, decode_upload(content, name), name)
        assert report["status"] == "rejected" and report["errors"][0]["raw"]
    assert len(store.query("SELECT * FROM batches")) == 2


def test_balanced_transfer_and_negative_adjustment(store):
    from consignai.services.analysis import compute

    base = compute(store, "2025-03-30")
    meta = {
        "source_id": "unit-test",
        "ingested_at": "2025-03-31T00:00:00Z",
        "record_type": "movement",
        "day": "2025-03-30",
        "sku": "sku0000",
    }
    report = ingest(
        store,
        [
            {
                **meta,
                "id": "test-transfer",
                "kind": "transfer",
                "quantity": 5,
                "from_location": "c000",
                "to_location": "f000",
            },
            {**meta, "id": "test-adjustment", "kind": "adjustment", "quantity": -2, "to_location": "f000"},
        ],
    )
    assert report["status"] == "accepted"
    after = compute(store, "2025-03-30")
    old = {(p["location_id"], p["sku"]): p["expected"] for p in base["positions"]}
    new = {(p["location_id"], p["sku"]): p["expected"] for p in after["positions"]}
    assert new["c000", "sku0000"] == old["c000", "sku0000"] - 5
    assert new["f000", "sku0000"] == old["f000", "sku0000"] + 3
    assert sum(new.values()) == sum(old.values()) - 2


def test_cross_owner_and_enterprise_stock_rejected(store):
    meta = {"source_id": "ownership-test", "ingested_at": "2025-04-01T00:00:00Z"}
    catalogs = [
        {
            **meta,
            "record_type": "location",
            "id": "other-enterprise",
            "owner_id": "other-enterprise",
            "kind": "enterprise",
            "name": "Other owner",
            "market": "National",
        },
        {
            **meta,
            "record_type": "location",
            "id": "other-contractor",
            "owner_id": "other-enterprise",
            "parent_id": "other-enterprise",
            "kind": "contractor",
            "name": "Other contractor",
            "market": "Chicago",
        },
    ]
    assert ingest(store, catalogs)["status"] == "accepted"
    movement = {
        **meta,
        "record_type": "movement",
        "id": "cross-owner-test",
        "sku": "sku0000",
        "day": "2025-03-30",
        "kind": "transfer",
        "quantity": 5,
        "from_location": "c000",
        "to_location": "other-contractor",
    }
    assert ingest(store, [movement])["status"] == "rejected"
    snapshot = {
        **meta,
        "record_type": "snapshot",
        "id": "root-stock",
        "sku": "sku0000",
        "day": "2025-03-30",
        "location_id": "enterprise",
        "on_hand": 50,
    }
    assert ingest(store, [snapshot])["status"] == "rejected"
