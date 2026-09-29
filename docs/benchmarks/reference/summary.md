# ConsignAI measured benchmark

Synthetic reference workload; not a production accuracy claim. Generated 2026-09-28T02:18:08.450586+00:00.

- Hardware: `{'platform': 'macOS-26.6.2-arm64-arm-64bit', 'machine': 'arm64', 'processor': 'arm', 'python': '3.12.14', 'numpy': '2.5.3'}`
- Model: disabled; no LLM calls
- Configuration: `{'seed': 42, 'contractors': 100, 'skus': 500, 'days': 365, 'slots': 8}`
- Records: 891,710; positions: 1,616

| Metric | Measured result |
|---|---:|
| Reconciliation | 1616/1616 |
| Anomaly precision | 97.56% |
| Anomaly recall | 100.00% |
| False-positive rate | 0.0377% |
| Forecast WAPE | 7.83% |
| 7-day forecast MAE | 2.171 units |
| Forecast holdouts | 2430 |
| Redistribution rule violations | 0 |
| Generate + validate + import | 38.347 s |
| Analysis | 2.919 s |
| Peak process RSS | 145.1 MiB |

Labels are intentionally obvious seeded scenarios. The detector can emit valid overlapping alerts not listed by the generator; see unexpected findings in results.json. Consumption forecasting is evaluated only on windows without observed zero stock, and does not estimate unmet demand. No external validation dataset is claimed.
