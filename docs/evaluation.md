# Evaluation and performance

Run from the repository root after installing Python dependencies:

```bash
python -m consignai.evaluation.benchmark
```

The command regenerates a fixed-seed dataset, imports into a fresh temporary database, computes an analysis, and writes `output/benchmark/results.json`, `metrics.csv`, `forecast.csv`, and `summary.md`. No existing app database is touched.

## Measures

1. **Reconciliation correctness:** an independent streaming Python replay computes balances directly from generated events. Every SQL-derived expected balance and reported variance is compared to that oracle.
2. **Detection precision/recall:** compare `(location, SKU, rule)` predictions against generator labels. Overallocated scenarios also label shortage because available units are zero. Precision is TP/(TP+FP); recall is TP/(TP+FN). Unexpected natural alerts remain false positives against this limited label set; they are not removed to improve the score.
3. **False-positive rate:** FP/(FP+TN) over five evaluated rules at every location/material position. This is not an alert-count percentage. Warehouses and sparse assignment assumptions affect the denominator.
4. **Forecast error:** three rolling seven-day holdouts, each using only its preceding 28 days. WAPE is total absolute error divided by total actual consumption. MAE is in seven-day units. Windows with an observed zero count or missing daily count are excluded, so the result is conditional on uncensored stock observations.
5. **Redistribution validity:** independently verify ownership, market, pack sizes, reconciled stock, enabled transfers, cumulative donor reserve and cumulative recipient capacity. The harness fails on any accounting mismatch or invalid proposal.

The detectors and labels are deliberately simple. High scores on these seeded synthetic patterns are not evidence of production precision, and false negatives in real missing-data regimes remain possible. No inventory loss is labeled theft. There is no field-validated business outcome, and proposal value is not savings.

## Measured example

The committed [reference summary](benchmarks/reference/summary.md) and [machine-readable output](benchmarks/reference/results.json) contain actual hardware, versions, parameters and results. This run occurred on macOS arm64 with Python 3.12.14 and NumPy 2.5.3; model execution was disabled. Timings are single local observations rather than multi-run confidence intervals. The final reference run was executed after the model smoke tests completed; timings remain development-machine observations, not controlled multi-run service benchmarks.

Peak RSS covers the whole benchmark process, including the independent replay, labels and holdout evaluation. It is not isolated server memory. The Windows standard library does not expose `resource`; memory reporting is unavailable there (reported as zero, not a zero-memory claim).

## Larger workloads

```bash
python -m consignai.evaluation.benchmark --contractors 250 --skus 1500 --slots 12 --days 365 --seed 42 --output output/large
python -m consignai.evaluation.benchmark --seed 7 --output output/seed-7
```

Results always include size, hardware and model metadata. Keep generated evidence and local databases outside Git. The `tests/benchmarks` suite runs a smaller smoke workload in normal testing. Use actual outputs when reporting performance; do not extrapolate throughput linearly.
