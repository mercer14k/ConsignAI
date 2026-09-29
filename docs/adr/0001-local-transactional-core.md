# ADR 0001 — SQLite and explicit analytical baselines

Status: accepted for the local reference release.

The suggested stack offered DuckDB/PostgreSQL, Polars and scikit-learn. This implementation uses Python's SQLite module and NumPy with FastAPI and React/Vite/ECharts.

The default workload needs atomic imports, immutable evidence, conflicting-ID rejection and a zero-setup local database. SQLite WAL provides transactions and portable read-only connections without a second server. DuckDB is better suited to columnar analytical scans and does not automatically support multiple writer processes. PostgreSQL remains the migration target for identity, tenant isolation, durable workers and large-scale projections. See [DuckDB concurrency documentation](https://duckdb.org/docs/lts/connect/concurrency).

Daily-window aggregation is performed by fixed SQL queries; NumPy implements median/MAD and winsorized means. Adding Polars or a scikit-learn model would not materially improve the present workload. The simple forecasting baseline is reproducible, auditable and evaluated out of time. More sophisticated methods should replace it only after outperforming it on representative data.

Consequences: one API process; run results are materialized as JSON; paging filters run projections in memory; integer quantities and simplified capacity; no claimed distributed database or globally optimal transfers. The service/data/domain separation makes a later storage and forecasting replacement explicit.
