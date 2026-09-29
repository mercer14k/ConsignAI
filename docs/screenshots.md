# Screenshots and visual verification

The PNGs in `docs/assets` are actual screenshots captured from the running application against its synthetic full-year API. They are not generated interface mockups.

After installing dependencies, activate the Python environment and run:

```bash
cd apps/web
pnpm exec playwright install chromium
pnpm e2e
```

The test runner starts the API on port 8077 and Vite on port 5177 when no compatible server is already running. A fresh server generates the full demo, so allow several minutes on a small machine. Tests run at 1600 × 1100 and at a 390 × 844 mobile viewport. They save full-page captures:

- `dashboard.png`: source-derived KPIs, trend, exceptions and market heatmap.
- `evidence.png`: filtered variance opened in the evidence drawer with a deterministic explanation.
- `redistribution.png`: proposal cards and explicit constraints.
- `mobile.png`: responsive overview.
- `model-picker.png`: explicit local model selection with no model selected; viewport capture so the modal backdrop remains consistent.

The automated checks also verify no page overflow on the mobile overview and no serious/critical axe-core violations on the desktop overview. This is useful evidence, not a complete accessibility certification. Verify keyboard flows and additional pages when changing the interface.

For a manual capture, use the same dimensions, wait for data to load, then take a full-page browser screenshot. Never replace real screenshot metrics with marketing numbers. Re-record after meaningful product changes and use the synthetic dataset and identify it as synthetic wherever screenshots are published. The in-app badge says Local dataset because workplace imports are also supported.
