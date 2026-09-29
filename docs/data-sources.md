# Bring your workplace into ConsignAI

**The demo uses generated data. A real deployment uses your organization's stock records.** ConsignAI is an analytical layer over those records; it is not an ERP, a source of physical counts, or a live integration with an external vendor.

The current input paths are canonical CSV/JSONL uploads, the import API, and the JSONL/JSONL.gz command-line importer. There are no built-in SAP, Oracle, Dynamics, NetSuite, WMS, spreadsheet, or database connectors. Exports from those systems can be mapped to the schema below. Their names describe possible upstream sources, not supported integrations.

## What to ask your operations team for

| Dataset | Likely owner / source | Fields to map | Why it matters |
|---|---|---|---|
| Location and contractor directory | ERP location master, vendor/contractor register, site register | Stable location ID, name, kind, market, enterprise owner, parent location, capacity, transfer eligibility | Separates legal ownership from physical custody and constrains transfers |
| Material master | ERP item master, procurement catalog | SKU, description, category, base unit, unit cost, replenishment lead time, pack size | Gives quantities a consistent meaning and sets replenishment constraints |
| Warehouse receipts and issues | WMS goods receipt / issue documents | Document-line ID, day, SKU, quantity, warehouse and recipient | Records stock entering the network and moving into contractor custody |
| Transfers and returns | WMS transfer journal, contractor return form, field material log | Document-line ID, day, SKU, quantity, source and destination | Moves custody without treating a transfer as consumption; contractor returns are transfers back to the warehouse |
| Actual field usage | Crew daily report, work-order consumption, contractor usage sheet | Record ID, day, SKU, quantity consumed, consuming location | Supports demand estimates; a warehouse issue is not proof of actual consumption |
| Daily on-hand and reservations | Contractor daily stock report, cycle counts, warehouse balances, field count app or spreadsheet | Count ID, closing day, SKU, physical location, reported on-hand, reserved units | Provides the independent reported stock to compare with the ledger |
| Approved stock adjustments | Inventory-control adjustment journal | Adjustment ID, day, SKU, signed quantity, affected location, reference | Makes authorized corrections explicit and traceable |

Reservations are part of each daily count in this version. Purchase orders, project schedules, invoices, delivery promises and an in-transit ledger are not currently modeled. Delivery lead time is a material-master input, not inferred from a purchasing integration.

## The minimum useful pilot

Pick one warehouse, a few contractors, one market and a consistent set of SKUs. Obtain the catalogs, an opening count, all subsequent movements and a later closing count. This is enough for reconciliation. Provide at least 28 complete calendar days of observations and actual usage for the consumption forecast; provide 60 days for inactivity rules. More history helps evaluation, but cannot repair missing or misclassified transactions.

**Do not calculate the reported count from the same ledger and then call the match a physical reconciliation.** Use independently reported counts when validating physical stock. If contractor counts are missing, ConsignAI cannot verify that contractor's physical inventory. A zero-filled spreadsheet is not a substitute for missing evidence.

The [illustrative import file](../apps/web/public/templates/workplace-example.jsonl) has ten records and can also be downloaded from **Data & imports → Start with your own data**. It demonstrates:

```text
Contractor: opening 20 + issue 10 − usage 4 = expected 26
           reported 24 − expected 26 = unexplained variance −2
Warehouse: opening 100 − issue 10 = expected and reported 90
```

These are examples, not business results. The two-day example intentionally has insufficient forecast history.

## Mapping rules that preserve accounting

1. **Use stable IDs.** Prefix source document IDs with the system and record type, and include the line number: `erp.issue.4500123.10`. Record IDs are globally unique across all types. Keep IDs and the complete record unchanged on replay; identical records become duplicates, conflicting records are rejected. Preserve the first `ingested_at` when resending the same record.
2. **Agree on the reporting cutoff.** A snapshot is an end-of-day count. The opening day's movements are already included in the opening count and are not replayed. Subsequent movements through the closing day are included. Normalize operational dates upstream; the engine does not perform timezone/cutoff conversion.
3. **Use consistent locations and SKUs.** Warehouse, contractor and field custody need different physical location IDs. Enterprise roots own stock but do not hold physical counts. Load parent locations before children. A contractor-to-field transfer needs both positions if you want to reconcile both sides.
4. **Normalize units upstream.** Current quantities are whole base units (`ea` or `m`) and costs are integer USD cents. Do not mix cases with pieces, fractional meters with whole meters, or currencies. Unit and currency conversion is not implemented.
5. **Classify movements once.** Map a receipt to one inbound leg, usage to one outbound leg, and issue/transfer to one record with both endpoints. Do not also import its two posting lines as separate stock events. Warehouse issues must originate at a warehouse; cross-owner transfers are rejected.
6. **Keep provenance.** Every record needs `source_id` and a timezone-aware `ingested_at`. Optional `lineage` is a string-to-string object, such as `{"system":"wms","export":"daily-2025-01-02","row":"17"}`. Do not embed credentials or unnecessary personal data.
7. **Retain corrections.** Evidence is immutable. Use approved signed adjustment events for accounting changes; a conflicting same-ID row is not an update. Corrections to historical snapshots/catalogs need a deliberate upstream rebuild into a separate database in this version. Do not invent an adjustment merely to eliminate a variance.

See the [data dictionary](data-model.md) for all fields and [JSON Schema](../data/schemas/record.schema.json) for the authoritative contract. `validation_status` is `valid` for accepted records; rejected raw rows remain in the batch report. CSV files should contain one record type with its relevant columns; JSONL can contain multiple types. Blank nullable endpoints in CSV become null; `lineage`, if supplied in CSV, contains quoted JSON. Extra columns are rejected rather than silently ignored. XLSX files need an upstream CSV/JSONL export.

## Start an empty workspace safely

Keep the demonstration database separate from workplace evidence. Disabling the seed does not remove data already in a database.

**Docker Compose:** in your local `.env`, set `DEMO_SEED=false` and `INVENTORY_DB_FILE=work.db`, then run `docker compose up -d --build`. This creates a separate database file in the existing persistent volume. Open the app and use its import screen; the original demo database is retained. Choose a different unused filename for another pilot.

**Native macOS/Linux:** stop your current API, then start it with a separate path:

```bash
DEMO_SEED=false CONSIGNAI_DB=var/work.db python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8077
```

**Native Windows PowerShell:**

```powershell
$env:DEMO_SEED="false"
$env:CONSIGNAI_DB="var/work.db"
.\.venv\Scripts\python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8077
```

The empty workspace exposes imports before the first analysis. Upload catalogs first, followed by counts and movements, review the visible validation reports, then click **Run analysis**. A rejected batch commits none of its inventory rows. Correct its mapping and retry with a new idempotency key. Successful imports make an existing analysis stale until it is rerun.

For a repeatable pilot using the illustrative file and a new database:

```bash
consignai import apps/web/public/templates/workplace-example.jsonl --db var/pilot-example.db
consignai analyze --db var/pilot-example.db
```

## Scheduled data feeds

Your scheduler or ETL job can export source data, transform it to the canonical schema, submit it, check `status` and `errors`, and run analysis only after acceptance. ConsignAI's weekly job analyzes records already imported; **it does not fetch fresh ERP data**.

```bash
curl --fail-with-body http://localhost:8077/api/v1/commands/import \
  -H 'Idempotency-Key: wms-export-2025-01-02-v1' \
  -F 'file=@mapped-movements.jsonl;type=application/x-ndjson'

# Check the report says "accepted" before running this:
curl --fail-with-body http://localhost:8077/api/v1/commands/analyze \
  -H 'Idempotency-Key: analysis-wms-export-2025-01-02-v1' \
  -H 'Content-Type: application/json' -d '{}'
```

An HTTP 200 import response can still contain `status: "rejected"`; inspect the report rather than the status code alone. HTTP uploads are limited to 20 MiB. Use ordered batches below that limit, or the JSONL command-line importer for larger files. Use the same idempotency key only for the exact same command/payload. Secured mode additionally requires the write credential in `X-API-Key`; supply it from your secret manager, not a committed script.

Before an organizational rollout, validate known stock positions against your system of record and follow the [security/deployment limitations](security.md). This reference implementation supports a local pilot; it does not supply enterprise SSO, tenant isolation or vendor-specific extraction.
