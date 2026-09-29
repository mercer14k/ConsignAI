import pytest
from consignai.data.generator import generate
from consignai.data.store import Store
from consignai.services.ingestion import ingest


@pytest.fixture
def store(tmp_path):
    db = Store(tmp_path / "test.db")
    report = ingest(db, generate(seed=42, contractors=10, skus=40, days=90, slots=4))
    assert report["status"] == "accepted"
    return db


@pytest.fixture
def tiny_records():
    return list(generate(seed=7, contractors=2, skus=3, days=35, slots=1))
