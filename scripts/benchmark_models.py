"""Compare local model adapters on identical evidence; no inventory mutation."""

import argparse
import json
import os
import platform
from pathlib import Path

from consignai.ai.explain import OllamaRuntime, explain
from consignai.data.store import Store
from consignai.services.analysis import compute, state_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="var/consignai.db")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("output/models.json"))
    args = parser.parse_args()
    store = Store(args.db)
    run = compute(store)
    before = state_digest(run)
    reports = []
    for model in args.models:
        runtime = OllamaRuntime(model=model, base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
        for alert in run["alerts"][: args.limit]:
            records = [
                json.loads(store.query("SELECT body FROM records WHERE id=?", (rid,))[0]["body"])
                for rid in alert["evidence_ids"]
            ]
            reports.append({"alert_id": alert["id"], **explain(alert, records, runtime)})
    assert state_digest(compute(store)) == before, "Model call changed deterministic results"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "run_id": run["id"],
                "dataset_version": run["dataset_version"],
                "state_unchanged": True,
                "results": reports,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "calls": len(reports),
                "accepted": sum(r["mode"] == "local_ai" for r in reports),
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
