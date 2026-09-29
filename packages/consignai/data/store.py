import contextlib
import json
import sqlite3
import threading
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, type TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS locations (id TEXT PRIMARY KEY, name TEXT, kind TEXT, market TEXT, owner_id TEXT, parent_id TEXT, capacity_units INTEGER, transfer_enabled INTEGER);
CREATE TABLE IF NOT EXISTS materials (id TEXT PRIMARY KEY, name TEXT, category TEXT, unit TEXT, unit_cost_cents INTEGER, lead_time_days INTEGER, pack_size INTEGER);
CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY REFERENCES records(id), day TEXT, sku TEXT REFERENCES materials(id), location_id TEXT REFERENCES locations(id), on_hand INTEGER, reserved INTEGER, UNIQUE(day, sku, location_id));
CREATE TABLE IF NOT EXISTS movements (id TEXT PRIMARY KEY REFERENCES records(id), day TEXT, sku TEXT REFERENCES materials(id), kind TEXT, quantity INTEGER, from_location TEXT REFERENCES locations(id), to_location TEXT REFERENCES locations(id));
CREATE TABLE IF NOT EXISTS legs (movement_id TEXT REFERENCES movements(id), day TEXT, sku TEXT, location_id TEXT, delta INTEGER, usage INTEGER);
CREATE INDEX IF NOT EXISTS idx_snap_position ON snapshots(location_id, sku, day);
CREATE INDEX IF NOT EXISTS idx_snap_day ON snapshots(day);
CREATE INDEX IF NOT EXISTS idx_legs_position ON legs(location_id, sku, day);
CREATE INDEX IF NOT EXISTS idx_legs_day ON legs(day);
CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, created_at TEXT, filename TEXT, report TEXT);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT, as_of TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS idempotency (key TEXT PRIMARY KEY, fingerprint TEXT, response TEXT);
CREATE TABLE IF NOT EXISTS jobs (period TEXT PRIMARY KEY, run_id TEXT, finished_at TEXT);
CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY, created_at TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
INSERT OR IGNORE INTO metadata VALUES ('data_version', '0');
"""


class Store:
    """One writer per process, WAL readers, short connections, immutable run snapshots."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as conn:
            conn.executescript(DDL)

    @contextlib.contextmanager
    def connect(self, readonly=False):
        uri = f"file:{self.path.resolve()}?mode=ro" if readonly else str(self.path)
        conn = sqlite3.connect(uri, uri=readonly, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if not readonly:
            conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            if not readonly:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql, args=()):
        with self.connect(readonly=True) as conn:
            return [dict(row) for row in conn.execute(sql, args)]

    def latest_run(self):
        rows = self.query("SELECT payload FROM runs ORDER BY created_at DESC, rowid DESC LIMIT 1")
        return json.loads(rows[0]["payload"]) if rows else None

    def version(self):
        return self.query("SELECT value FROM metadata WHERE key='data_version'")[0]["value"]
