# Data model and dictionary

All records have `id` (stable globally unique identifier), `source_id` (dataset identifier), `ingested_at` (timezone-aware source ingestion timestamp), `validation_status` (`valid`), and optional string-to-string `lineage`. Actual receiving time is also recorded in the batch report. Synthetic source timestamps are fixed for reproducibility; they are not represented as the current import time.

| Record | Required business fields | Meaning |
|---|---|---|
| Location | `name`, `kind`, `market` | Enterprise, warehouse, contractor or field node |
| Location | `owner_id`, `parent_id`, `capacity_units`, `transfer_enabled` | Ownership, hierarchy and transfer constraints; defaults documented in schema |
| Material | `name`, `category`, `unit`, `unit_cost_cents`, `lead_time_days`, `pack_size` | SKU economics and constraints |
| Movement | `day`, `sku`, `kind`, `quantity`, endpoint fields | A dated, signed-effect inventory event |
| Snapshot | `day`, `sku`, `location_id`, `on_hand`, `reserved` | End-of-day reported count and reservations |

The authoritative machine-readable contract is [record.schema.json](../data/schemas/record.schema.json), generated from Pydantic with `python scripts/generate_schemas.py`.

## Movement semantics

| Kind | Source | Destination | Quantity | Ledger effect |
|---|---|---|---|---|
| receipt | absent | required | positive | inbound to destination |
| issue | warehouse | different location | positive | equal outbound and inbound legs |
| transfer | required | different location | positive | equal outbound and inbound legs |
| usage | required | absent | positive | outbound consumption |
| adjustment | absent | required | positive or negative, nonzero | signed adjustment to destination |

No cross-owner movements are accepted. All foreign keys must already exist in the database or earlier in the batch. Locations require an enterprise owner and an existing parent. The supplied demo uses one enterprise. Capacity is a simplified sum of integral base units; it is not volumetric capacity. Mixed physical units cannot be compared as engineering volume.

**Reconciliation:** `expected = opening_on_hand + net_ledger_movements`; `variance = latest_reported - expected`. Opening-day movements are excluded because that closing count already incorporates them. Snapshot uniqueness is `(day, location, SKU)`.

Quantities use integer base units (`ea` or whole meters), and USD values use integer cents. Decimal stock units, FX, valuation layers, purchase orders, lots, expiry and serial numbers are not modeled. Reservations may exceed stock; this is an operational over-allocation alert, not invalid data.

## Physical ownership and totals

Enterprise is the owner hierarchy, not an additional physical stock position. Network stock value sums warehouse, contractor and field stock once; enterprise ownership is not double-counted. Transfers leave network quantity unchanged. Receipts, consumption and adjustments change network quantity.

## Synthetic data

`seed=42`, 100 contractors, 500 SKUs, 365 days starting 2025-01-01, eight SKUs per contractor, ten field sites and five warehouses. Each SKU appears in the catalog; stock is held only at assigned locations. The default measured dataset contains 891,710 records and 1,616 location/material positions.

Seeded scenarios: unrecorded loss, final-day usage spike, inactivity, replenishment interruption and over-allocation. Generator truth is written separately and never passed to detection. Ordinary stochastic consumption can also trigger legitimate rules, which is why measured precision is not forced to 100%.

A small [committed fixture](../data/sample/mini.jsonl.gz) contains five contractors, 15 SKUs and 70 days. It is intended for an empty database, not to overwrite the full demo catalog. `ground-truth.json` describes its seeded scenarios. Generated network data includes receipts, issues, usage and adjustments. Balanced transfers are covered by dedicated integration tests.

## Invalid data

JSONL and CSV uploads are limited to 20 MiB. The request body is capped before multipart parsing at 21 MiB, including framing. Unicode errors, malformed JSON, invalid lineage, negative counts, invalid endpoints, unknown references, duplicate snapshot keys and conflicting IDs are rejected. Reports retain invalid rows; successful rows in a rejected batch never commit. Empty batches are rejected. Uploads are data only: no formulas, SQL or shell code are executed.

For actual upstream sources, column-mapping rules and a separate workplace database, see [Bring your workplace into ConsignAI](data-sources.md).
