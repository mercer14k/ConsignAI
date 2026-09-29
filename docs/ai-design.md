# AI design

The computational core runs with no model selected. There is no model default or global model selection. It performs inventory accounting, robust anomaly rules, time-series estimation and constrained allocation independently of a language model.

## Explicit analytical models

- **Variance:** latest reported quantity minus the balance replayed from the opening count.
- **Usage anomaly:** final-day usage above prior-calendar-day median plus `max(8, 6 × 1.4826 × MAD)` in a 28-day window.
- **Inactivity:** no recorded consumption for 60 days, with nonzero stock and enough history. Warehouse holdings are excluded from consumption inactivity rules.
- **Coverage:** nonnegative available units, after reservations, divided by a 28-day mean winsorized at the 95th percentile. Missing recent daily counts or insufficient history suppress the estimate. Zero demand produces null coverage, not an invented infinity. Zero-stock observations are labeled as censored demand.
- **Shortage:** forecast coverage below SKU lead time. Over-allocation can cause an independent shortage finding.
- **Staleness:** more than two days since the latest count. Other findings and coverage are suppressed for stale positions.
- **Risk:** sum of explicit severity weights, capped at 100 per position. Market/contractor heatmaps aggregate these weights; they are not probabilities.
- **Market and contractor coverage:** aggregate available units divided by aggregate demand for eligible observed positions. This hides mix effects and must be read alongside SKU-level shortages.

## Redistribution

Greedy candidates prioritize the shortest coverage. Each transfer must use the same SKU, owner and market, meet pack multiples, protect reservations, retain donor cover of 45 days (or at least 25 units), and respect the recipient's shared capacity budget. Eligible donors need fresh, reconciled counts and sufficient consumption history, except warehouses, which retain the explicit minimum reserve. Recipient target cover is the larger of 21 days and SKU lead time plus seven days. A two-day transfer assumption flags urgent cases requiring expediting.

Shared donor and recipient budgets prevent reuse across proposals. No proposal implies fulfillment, stock movement, transportation availability, cost savings or mathematical optimality.

## Local language model contract

`Runtime` is a protocol; `OllamaRuntime` is the implemented adapter. Business logic depends only on the protocol, so other local runtimes can be added without changing accounting. The user explicitly chooses a locally installed model through the sidebar picker. Selection is held in page memory and sent per explanation request as `{"model":"exact-installed-name"}`; it clears on reload. Omitting the body, sending `{}`, or sending `{"model":null}` produces a deterministic brief with no runtime calls. Legacy `AI_RUNTIME` and `OLLAMA_MODEL` variables are ignored. Qwen2.5 1.5B and Qwen3 8B were explicitly tested; their artifact names do not establish a default.

Ollama receives a system instruction plus an explicitly untrusted evidence object. It is given the Pydantic explanation JSON schema. Accepted output contains status, a brief qualitative summary, cited record IDs and an allowlisted next-action suggestion. The Ollama schema restricts the summary to a vetted rule-specific brief or an abstention, and restricts citation choices to the supplied evidence IDs. This version evaluates constrained narrative selection rather than unrestricted text generation. It cannot invent a new root-cause explanation. Unknown fields, foreign citations, missing citations and numeric narrative claims are rejected. The UI displays authoritative numerical results separately. Model output never supplies balances, KPI values, statistical results or workflow state.

A schema is not a factuality guarantee. The prompt treats retrieved strings as untrusted; no model-generated command or SQL is ever executed. There are **no model tools**, and no mutation capability is exposed to the model. Users must still review narrative claims. Evidence absent from the required record set triggers deterministic abstention. Timeouts, invalid schemas and invalid citations return the deterministic brief and report the failure.

The committed explicit-model smoke output records a valid abstention from the final adapter; earlier free-form output failures are retained separately to demonstrate fallback behavior.

No private chain-of-thought is requested or persisted. Thinking is disabled when supported. Observable telemetry records the runtime/model, prompt version, parameters, data version, source IDs, record IDs, trace/run ID, latency, retry count, validation failures and tokens when available. Retries are zero by design. Endpoint hosts are restricted to explicit local addresses or the Compose service name; proxies are disabled for local requests.

## Discovery and local-only boundary

`GET /api/v1/ai/models` uses Ollama's [installed model catalog](https://docs.ollama.com/api/tags). It exposes names, weight sizes, parameter sizes, quantization and digests; it never chooses a model or downloads weights. Empty, unreachable and malformed catalogs produce visible states. The read authorization boundary applies to discovery, and the command authorization boundary applies to explanation requests.

Only entries with positive local weight size and GGUF metadata are listed. Remote model/host metadata, cloud-labelled entries and known non-completion models are excluded. Before each generation, the adapter fetches the catalog again and inspects `/api/show` for local weights and completion capability. A missing/changed/unsupported selection fails into the deterministic fallback without a chat request. The reply must identify the requested model and must not identify a remote model or host. Telemetry records the requested model and verified digest, alongside existing evidence/run metadata. Some runtimes do not report capabilities in the catalog; those models can appear in the picker but are verified through `show` before use.

The trusted boundary is the operator-controlled local runtime. A maliciously replaced local server is outside this application boundary. Disable Ollama cloud features with its documented `OLLAMA_NO_CLOUD=1` setting (set in the optional Compose service); see [Ollama's FAQ](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features). The API endpoint is server-configured, restricted to allowed local hosts, and cannot be overridden by an explanation payload. This does not discover models on a remote browser client's machine.

## Benchmark local models

```bash
python scripts/benchmark_models.py --models YOUR_INSTALLED_MODEL ANOTHER_INSTALLED_MODEL --limit 5
```

Models must be installed in Ollama first. This compares schema/citation acceptance and latency on identical evidence while asserting that deterministic state remains unchanged. It does not claim semantic quality or general model capability.
