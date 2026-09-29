# Public project launch kit

## Repository metadata

**Name:** consignai

**Description:** Evidence-first intelligence for contractor and field inventory. Reconciliation, anomaly detection, forecasting and constrained redistribution—with optional local AI.

**Topics:** inventory-management, supply-chain, consignment, fastapi, python, react, forecasting, anomaly-detection, ollama, local-ai, open-source, operations-research

## Suggested launch post

I built ConsignAI to answer a practical operations question: “We issued the stock. Where did it go—and who needs it next?”

It reconciles contractor and field counts against a movement ledger, flags discrepancies and shortages, and proposes redistribution without spending the same donor stock twice. Every finding opens the source evidence.

The demo runs locally, uses no paid AI APIs, and works with the LLM switched off. The repository includes a full-year synthetic network, a reproducible evaluation harness, real benchmark outputs, and the limitations behind those numbers.

Start with the dashboard screenshot, follow a variance into the ledger, then inspect the accounting code. I’d welcome feedback from materials managers and engineers working on field inventory.

[Add your repository link after publishing.]

## A 60-second demo

- 0–10s: overview, synthetic dataset label and source-derived metrics.
- 10–25s: Exceptions → variance → evidence drawer. Show opening + movements = expected.
- 25–35s: request the deterministic explanation and expand supporting record IDs.
- 35–45s: redistribution proposal, reserve/pack/capacity constraints, proposal-only status.
- 45–55s: rejected upload and unchanged ledger; export exception CSV.
- 55–60s: measured benchmark and explicit limitations.

Lead with the operational problem and proof. Avoid unsupported savings, customer adoption, “production-ready”, fabricated stars, or claims that benchmark scores generalize to real stockrooms. Reach depends on distribution and audience fit; no README can guarantee it.
