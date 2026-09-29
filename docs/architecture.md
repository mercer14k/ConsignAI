# Architecture

ConsignAI is a local operations system with a deterministic accounting boundary. FastAPI orchestrates services; domain functions have no HTTP, database, or model dependency. React presents API results and never computes inventory balances or risk scores.

## Data flow

1. A generator, CSV, or JSONL file supplies canonical records.
2. Pydantic validates schema, then ingestion checks references and identifier conflicts inside a database transaction.
3. Valid records and movement legs commit together. Any invalid record rolls back the entire batch. A separate batch report retains rejected row content and errors.
4. Analysis reads one consistent SQLite snapshot. It reconciles each physical location/material position, forecasts eligible consumption, detects exceptions, and allocates proposal budgets.
5. An immutable run stores the parameters, data version, positions, alerts, market/contractor rollups and transfer candidates.
6. The API serves a run by ID. The evidence drawer loads the exact opening/latest snapshots and paginated movement records behind that run.
7. Optional Ollama narration receives a scoped evidence object. Its only output is a validated explanation; it cannot write to the ledger.

The editable [Mermaid source](architecture.mmd) and [canonical diagram](architecture.diagram.json) describe this boundary. Static validation was performed; host-specific Mermaid rendering is left to GitHub.

## Deployment and concurrency

The default Compose deployment has one API process, an unprivileged Nginx frontend, and a named inventory volume. The optional `ai` profile adds Ollama. All host ports bind to loopback. The browser uses the Nginx API proxy, so no cross-origin API permissions are necessary.

SQLite WAL permits concurrent read connections. A process-local reentrant lock serializes mutation services and the weekly scheduler. Readers use `mode=ro`. **Run one API worker.** Multiple processes may use SQLite sequentially, but they do not share the process lock; multi-worker scheduling and cross-process idempotency are outside this version's guarantee. Native offline import should be performed with the API stopped.

The scheduler checks the UTC ISO-week period on startup and hourly while the API is running. A persisted completion key prevents repeated weekly analysis in normal operation and performs catch-up after downtime. No uptime guarantee or exactly-once claim is made across a process crash between run and job commit.

## Integrity choices

- Opening count is a close-of-day accounting anchor; only movements after its date enter the reconciliation.
- Latest reported count is the reconciliation cutoff, even if the run date is later.
- Source records cannot be edited in place. Corrections use explicit adjustments or a fresh dataset. Same-ID conflicts fail visibly.
- Same content imported twice is counted as a duplicate. Idempotency keys replay completed command results and reject reuse with different input.
- Analysis results are snapshots, not live mutable workflow objects. The UI marks results stale after a new accepted import.
- Proposal values are stock values, **not savings**. Proposals do not create transfers or consume inventory.

## Scale boundary

The sample network is sparse: 500 catalog SKUs, eight assignments per contractor, matching warehouse holdings, and field sites. It is not a 100 × 500 dense stock matrix. Full-year evidence is generated locally, not bundled into Git. Materialized run JSON is convenient at this scale; paging currently filters that run in memory. Large multi-tenant workloads should move projections, pagination and jobs to PostgreSQL and a durable worker queue.
