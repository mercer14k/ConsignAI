# Threat model

## Assets and boundaries

Assets are inventory evidence, contractor names, analysis results, API credentials and local model context. Boundaries are browser→API, uploaded data→parser, parser→SQLite, scoped evidence→local model, and model output→UI. This is a single-enterprise local reference implementation, not a multi-tenant hosted service.

| Threat | Implemented control | Residual risk |
|---|---|---|
| Malformed or oversized upload | 21 MiB whole-body cap before multipart parsing; 20 MiB file cap; MIME/extension checks; typed schema; transaction rollback | Many concurrent maximum-sized requests can exhaust resources; reverse-proxy rate limits are needed for public hosting |
| Path traversal | Sanitized display basename; uploaded names never become filesystem paths | Invalid raw content remains in quarantine reports |
| SQL injection | Parameterized user values; fixed queries; model has no SQL tool | A future connector must preserve this boundary |
| Formula injection in exports | Spreadsheet-control leading characters are escaped | Recipients should still treat external CSV as untrusted |
| Unauthorized writes | Separate read bearer and write API-key dependencies in secured mode; insufficient/default keys fail startup | Shared keys are not SSO, per-person identity, tenant authorization or fine-grained policy |
| Browser CSRF / rebinding | Explicit local Origin allowlist, Host allowlist, no broad CORS; Compose loopback binding | Native local processes can access demo mode; never expose demo mode to untrusted networks |
| Prompt injection | Retrieved strings are untrusted; no tools; local host allowlist; typed output and evidence validation | Textual hallucination can survive schema checks; narrative is advisory |
| Model outage or malformed response | Timeout and deterministic fallback; no mutation handle | Narration latency consumes a worker thread |
| Silent evidence overwrite | Stable IDs, content hashes, conflicts rejected, immutable run snapshots | Source systems can still send plausible wrong data |
| Compromised dependency | Version lockfiles, pip-audit, pnpm audit, open-source license inventory | Scanners have incomplete coverage; base images and actions need routine review |
| Data leakage | No analytics, external fonts, cloud AI or automatic outbound connectors; API/AI logs omit full row bodies | Imported invalid rows are retained in reports; OS and storage access are trusted |

## Operational posture

`APP_MODE=demo` allows reads and writes for the loopback demo. `APP_MODE=secured` requires different `READ_API_KEY` and `WRITE_API_KEY` values of at least 24 characters. Use bearer authorization for reads and `X-API-Key` for commands. The UI credential dialog stores them only in memory. Never place secrets in client build variables, URLs, the repository, screenshots or benchmark outputs.

Read services open SQLite using read-only connection mode. There are no database credentials in SQLite. The API container uses a non-root user and drops Linux capabilities; Nginx runs unprivileged with security headers. The optional model service is available only within the Compose network. The default application requires no model download.

Before handling real organizational data: deploy behind authenticated TLS, adopt organizational identity and per-location authorization, validate tenant boundaries, configure request-rate limits, encrypt and back up the volume, define data retention and incident procedures, rotate secrets, review model licenses, and test recovery. Do not bind demo ports to `0.0.0.0` on an untrusted network.

Corrections are explicit adjustments; do not delete evidence to silence alerts. The system does not execute model-generated code, SQL or transfer actions.

Model selection is explicit and per request. Discovery requires read authorization. The adapter rejects remote/cloud aliases and verifies local completion capabilities before sending evidence. Runtime hosts cannot be supplied by a browser payload. Models are never downloaded automatically. See [AI design](ai-design.md) for the trusted-local-runtime boundary and cloud-disable configuration.
