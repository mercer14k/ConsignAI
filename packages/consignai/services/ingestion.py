"""Atomic batch import: either all valid rows commit, or every write rolls back.

Invalid rows are retained in a visible report. Same-ID same-content rows are
counted as duplicates; conflicting identifiers never overwrite prior evidence.
"""

import csv
import hashlib
import io
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath

from pydantic import ValidationError

from consignai.domain.schemas import Location, Material, Movement, Snapshot, record_adapter


def now():
    return datetime.now(timezone.utc).isoformat()


def decode_upload(data: bytes, filename: str):
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        yield {"_invalid_utf8_hex": data.hex()}
        return
    if filename.lower().endswith(".csv"):
        for row in csv.DictReader(io.StringIO(content)):
            if "lineage" in row:
                try:
                    row["lineage"] = json.loads(row["lineage"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    yield {"_malformed_csv_lineage": row}
                    continue
            for name in ("from_location", "to_location", "parent_id"):
                if name in row and not row[name]:
                    row[name] = None
            yield row
    else:
        for line in content.splitlines():
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    yield {"_malformed_json": line}


def ingest(store, records, filename="generated", batch_id=None):
    batch_id = batch_id or str(uuid.uuid4())
    report = {
        "id": batch_id,
        "created_at": now(),
        "filename": PurePosixPath(filename.replace("\\", "/")).name[:120],
        "status": "accepted",
        "rows": 0,
        "accepted": 0,
        "duplicates": 0,
        "errors": [],
    }
    with store.lock, store.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for index, raw in enumerate(records, 1):
            report["rows"] = index
            try:
                record = record_adapter.validate_python(raw)
                body = record.model_dump_json()
                digest = hashlib.sha256(body.encode()).hexdigest()
                existing = conn.execute("SELECT hash FROM records WHERE id=?", (record.id,)).fetchone()
                if existing:
                    if existing["hash"] != digest:
                        raise ValueError("ID conflicts with existing evidence")
                    report["duplicates"] += 1
                    continue
                conn.execute("SAVEPOINT row_import")
                conn.execute(
                    "INSERT INTO records VALUES (?,?,?,?)", (record.id, record.record_type, digest, body)
                )
                if isinstance(record, Location):
                    if record.kind == "enterprise" and (record.owner_id != record.id or record.parent_id):
                        raise ValueError("enterprise root must own itself and have no parent")
                    if (
                        record.kind != "enterprise"
                        and not conn.execute(
                            "SELECT 1 FROM locations WHERE id=? AND kind='enterprise'", (record.owner_id,)
                        ).fetchone()
                    ):
                        raise ValueError("owner_id must reference an imported enterprise")
                    if (
                        record.parent_id
                        and not conn.execute(
                            "SELECT 1 FROM locations WHERE id=?", (record.parent_id,)
                        ).fetchone()
                    ):
                        raise ValueError("parent_id must reference an imported location")
                    conn.execute(
                        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?)",
                        (
                            record.id,
                            record.name,
                            record.kind,
                            record.market,
                            record.owner_id,
                            record.parent_id,
                            record.capacity_units,
                            record.transfer_enabled,
                        ),
                    )
                elif isinstance(record, Material):
                    conn.execute(
                        "INSERT INTO materials VALUES (?,?,?,?,?,?,?)",
                        (
                            record.id,
                            record.name,
                            record.category,
                            record.unit,
                            record.unit_cost_cents,
                            record.lead_time_days,
                            record.pack_size,
                        ),
                    )
                elif isinstance(record, Snapshot):
                    location = conn.execute(
                        "SELECT kind FROM locations WHERE id=?", (record.location_id,)
                    ).fetchone()
                    if location and location[0] == "enterprise":
                        raise ValueError("snapshots need a physical stock location, not an enterprise root")
                    conn.execute(
                        "INSERT INTO snapshots VALUES (?,?,?,?,?,?)",
                        (
                            record.id,
                            str(record.day),
                            record.sku,
                            record.location_id,
                            record.on_hand,
                            record.reserved,
                        ),
                    )
                elif isinstance(record, Movement):
                    if conn.execute(
                        "SELECT 1 FROM locations WHERE id IN (?,?) AND kind='enterprise'",
                        (record.from_location, record.to_location),
                    ).fetchone():
                        raise ValueError("movements need physical stock locations")
                    locs = [
                        r["owner_id"]
                        for r in conn.execute(
                            "SELECT owner_id FROM locations WHERE id IN (?,?)",
                            (record.from_location, record.to_location),
                        )
                    ]
                    if len(set(locs)) > 1:
                        raise ValueError("cross-owner movement needs an ownership workflow")
                    if record.kind == "issue":
                        src = conn.execute(
                            "SELECT kind FROM locations WHERE id=?", (record.from_location,)
                        ).fetchone()
                        if not src or src[0] != "warehouse":
                            raise ValueError("issue must originate at a warehouse")
                    conn.execute(
                        "INSERT INTO movements VALUES (?,?,?,?,?,?,?)",
                        (
                            record.id,
                            str(record.day),
                            record.sku,
                            record.kind,
                            record.quantity,
                            record.from_location,
                            record.to_location,
                        ),
                    )
                    if record.from_location:
                        conn.execute(
                            "INSERT INTO legs VALUES (?,?,?,?,?,?)",
                            (
                                record.id,
                                str(record.day),
                                record.sku,
                                record.from_location,
                                -record.quantity,
                                record.quantity if record.kind == "usage" else 0,
                            ),
                        )
                    if record.to_location:
                        conn.execute(
                            "INSERT INTO legs VALUES (?,?,?,?,?,0)",
                            (record.id, str(record.day), record.sku, record.to_location, record.quantity),
                        )
                conn.execute("RELEASE row_import")
                report["accepted"] += 1
            except (ValidationError, ValueError, sqlite3.IntegrityError) as exc:
                # A failed row cannot pollute subsequent validation through partial inserts.
                if conn.in_transaction:
                    try:
                        conn.execute("ROLLBACK TO row_import")
                        conn.execute("RELEASE row_import")
                    except sqlite3.OperationalError:
                        pass
                report["errors"].append(
                    {
                        "row": index,
                        "record_id": raw.get("id") if isinstance(raw, dict) else None,
                        "message": str(exc)[:1500],
                        "raw": raw,
                    }
                )
        if report["errors"] or not report["rows"]:
            conn.rollback()
            report["status"] = "rejected"
            report["accepted"] = 0
            if not report["rows"]:
                report["errors"].append({"row": 0, "message": "Empty batch", "raw": None})
        elif report["accepted"]:
            conn.execute("UPDATE metadata SET value=CAST(value AS INTEGER)+1 WHERE key='data_version'")
        conn.execute(
            "INSERT INTO batches VALUES (?,?,?,?)",
            (batch_id, report["created_at"], report["filename"], json.dumps(report)),
        )
    return report
