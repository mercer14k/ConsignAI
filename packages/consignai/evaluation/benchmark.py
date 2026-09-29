"""Reproducible evaluation; labels never enter production analysis."""

import argparse
import csv
import importlib.metadata
import json
import math
import platform

try:
    import resource
except ImportError:  # Windows has no resource module.
    resource = None
import tempfile
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from consignai.data.generator import generate, ground_truth
from consignai.data.store import Store
from consignai.domain.engine import forecast
from consignai.services.analysis import compute
from consignai.services.ingestion import ingest, now


def transfer_validity(run):
    positions = {(p["location_id"], p["sku"]): p for p in run["positions"]}
    outgoing = Counter()
    incoming = Counter()
    violations = []
    for t in run["transfers"]:
        a = positions[t["from_location"], t["sku"]]
        b = positions[t["to_location"], t["sku"]]
        if (
            a["owner_id"] != b["owner_id"]
            or a["market"] != b["market"]
            or t["quantity"] <= 0
            or t["quantity"] % b["pack_size"]
            or a["variance"]
            or b["variance"]
            or not a["transfer_enabled"]
            or not b["transfer_enabled"]
        ):
            violations.append(t["id"])
        outgoing[t["from_location"], t["sku"]] += t["quantity"]
        incoming[t["to_location"]] += t["quantity"]
    for key, n in outgoing.items():
        a = positions[key]
        if n > a["available"] - max(25, math.ceil((a["daily_demand"] or 0) * 45)):
            violations.append(str(key))
    for loc, n in incoming.items():
        group = [p for p in run["positions"] if p["location_id"] == loc]
        if sum(p["on_hand"] for p in group) + n > group[0]["capacity_units"]:
            violations.append(loc)
    return {"proposals": len(run["transfers"]), "violations": violations, "valid": not violations}


def evaluate(output=Path("output/benchmark"), seed=42, contractors=100, skus=500, days=365, slots=8):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = dict(seed=seed, contractors=contractors, skus=skus, days=days, slots=slots)
    started = time.perf_counter()
    expected = {}
    reported = {}
    usage = defaultdict(dict)
    snapshots = defaultdict(dict)
    count = 0

    def stream():
        nonlocal count
        for r in generate(**config):
            count += 1
            if r["record_type"] == "snapshot":
                key = (r["location_id"], r["sku"])
                expected.setdefault(key, r["on_hand"])
                reported[key] = r["on_hand"]
                snapshots[key][r["day"]] = r["on_hand"]
            elif r["record_type"] == "movement":
                # Independent ledger replay; no analysis query or balance helper is reused.
                for loc, sign in ((r["from_location"], -1), (r["to_location"], 1)):
                    if loc:
                        key = (loc, r["sku"])
                        expected[key] += sign * r["quantity"]
                if r["kind"] == "usage":
                    usage[(r["from_location"], r["sku"])][r["day"]] = (
                        usage[(r["from_location"], r["sku"])].get(r["day"], 0) + r["quantity"]
                    )
            yield r

    with tempfile.TemporaryDirectory(prefix="consignai-eval-") as tmp:
        store = Store(Path(tmp) / "benchmark.db")
        imported = ingest(store, stream())
        if imported["status"] != "accepted":
            raise RuntimeError(imported["errors"][:2])
        import_seconds = time.perf_counter() - started
        analysis_started = time.perf_counter()
        run = compute(store)
        analysis_seconds = time.perf_counter() - analysis_started
        labels = {(r["location_id"], r["sku"], r["kind"]) for r in ground_truth(**config)}
        # An overallocated position also has zero available days of supply by construction.
        labels |= {(loc, sku, "shortage") for loc, sku, kind in list(labels) if kind == "overallocated"}
        found = {(a["location_id"], a["sku"], a["kind"]) for a in run["alerts"] if a["kind"] != "stale"}
        tp = len(labels & found)
        fp = len(found - labels)
        fn = len(labels - found)
        universe = len(run["positions"]) * 5
        tn = universe - tp - fp - fn
        correct = sum(
            p["expected"] == expected[(p["location_id"], p["sku"])]
            and p["variance"]
            == reported[(p["location_id"], p["sku"])] - expected[(p["location_id"], p["sku"])]
            for p in run["positions"]
        )
        forecast_rows = []
        end = date.fromisoformat(run["as_of"])
        for horizon_back in (7, 14, 21):
            cutoff = end - timedelta(days=horizon_back)
            history = [str(cutoff - timedelta(days=i)) for i in reversed(range(28))]
            future = [str(cutoff + timedelta(days=i)) for i in range(1, 8)]
            for key, values in usage.items():
                if not key[0].startswith(("c", "f")) or not all(
                    d in snapshots[key] for d in history + future
                ):
                    continue
                if any(snapshots[key][d] == 0 for d in history + future):
                    continue
                prediction = forecast([values.get(d, 0) for d in history])["daily_demand"] * 7
                actual = sum(values.get(d, 0) for d in future)
                forecast_rows.append(
                    {
                        "location_id": key[0],
                        "sku": key[1],
                        "cutoff": str(cutoff),
                        "predicted_7d": prediction,
                        "actual_7d": actual,
                        "absolute_error": abs(prediction - actual),
                    }
                )
        error = sum(r["absolute_error"] for r in forecast_rows)
        actual_total = sum(r["actual_7d"] for r in forecast_rows)
        by_rule = {}
        for kind in ("variance", "usage_spike", "inactive", "shortage", "overallocated"):
            labeled = {r for r in labels if r[2] == kind}
            f = {r for r in found if r[2] == kind}
            by_rule[kind] = {"tp": len(labeled & f), "fp": len(f - labeled), "fn": len(labeled - f)}
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else 0
        result = {
            "generated_at": now(),
            "config": config,
            "hardware": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python": platform.python_version(),
                "numpy": importlib.metadata.version("numpy"),
            },
            "model": {"runtime": "none", "model": None},
            "algorithm_version": run["algorithm_version"],
            "dataset": {
                "records": count,
                "positions": len(run["positions"]),
                "contractors": contractors,
                "skus": skus,
                "days": days,
            },
            "performance": {
                "generate_validate_import_seconds": round(import_seconds, 3),
                "analysis_seconds": round(analysis_seconds, 3),
                "total_seconds": round(time.perf_counter() - started, 3),
                "peak_rss_mib": round(peak / (1024**2 if platform.system() == "Darwin" else 1024), 1),
                "rss_scope": "whole benchmark process including independent replay and forecast evaluation",
            },
            "reconciliation": {
                "correct": correct,
                "total": len(run["positions"]),
                "accuracy": correct / len(run["positions"]),
            },
            "detection": {
                "precision": tp / (tp + fp) if tp + fp else None,
                "recall": tp / (tp + fn) if tp + fn else None,
                "false_positive_rate": fp / (fp + tn) if fp + tn else None,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "by_rule": by_rule,
                "unexpected": sorted(found - labels),
                "missed": sorted(labels - found),
            },
            "forecast": {
                "wape": error / actual_total if actual_total else None,
                "mae_7d_units": error / len(forecast_rows) if forecast_rows else None,
                "windows": len(forecast_rows),
                "method": "28-day winsorized mean; three rolling 7-day holdouts; zero-stock windows excluded",
            },
            "redistribution": transfer_validity(run),
        }
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (output / "forecast.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            lineterminator="\n",
            fieldnames=["location_id", "sku", "cutoff", "predicted_7d", "actual_7d", "absolute_error"],
        )
        writer.writeheader()
        writer.writerows(forecast_rows)
    with (output / "metrics.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerows(
            [
                ["reconciliation_accuracy", result["reconciliation"]["accuracy"]],
                ["precision", result["detection"]["precision"]],
                ["recall", result["detection"]["recall"]],
                ["false_positive_rate", result["detection"]["false_positive_rate"]],
                ["forecast_wape", result["forecast"]["wape"]],
                ["analysis_seconds", analysis_seconds],
            ]
        )
    d = result["detection"]
    fc = result["forecast"]
    pf = result["performance"]
    (output / "summary.md").write_text(
        f"# ConsignAI measured benchmark\n\nSynthetic reference workload; not a production accuracy claim. Generated {result['generated_at']}.\n\n- Hardware: `{result['hardware']}`\n- Model: disabled; no LLM calls\n- Configuration: `{config}`\n- Records: {count:,}; positions: {len(run['positions']):,}\n\n| Metric | Measured result |\n|---|---:|\n| Reconciliation | {correct}/{len(run['positions'])} |\n| Anomaly precision | {d['precision']:.2%} |\n| Anomaly recall | {d['recall']:.2%} |\n| False-positive rate | {d['false_positive_rate']:.4%} |\n| Forecast WAPE | {fc['wape']:.2%} |\n| 7-day forecast MAE | {fc['mae_7d_units']:.3f} units |\n| Forecast holdouts | {fc['windows']} |\n| Redistribution rule violations | {len(result['redistribution']['violations'])} |\n| Generate + validate + import | {pf['generate_validate_import_seconds']} s |\n| Analysis | {pf['analysis_seconds']} s |\n| Peak process RSS | {pf['peak_rss_mib']} MiB |\n\nLabels are intentionally obvious seeded scenarios. The detector can emit valid overlapping alerts not listed by the generator; see unexpected findings in results.json. Consumption forecasting is evaluated only on windows without observed zero stock, and does not estimate unmet demand. No external validation dataset is claimed.\n"
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/benchmark"))
    for k, v in [("seed", 42), ("contractors", 100), ("skus", 500), ("days", 365), ("slots", 8)]:
        parser.add_argument("--" + k, type=int, default=v)
    result = evaluate(**vars(parser.parse_args()))
    print(json.dumps(result, indent=2))
    if result["reconciliation"]["accuracy"] != 1 or not result["redistribution"]["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
