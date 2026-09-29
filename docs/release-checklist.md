# Release checklist

## Implemented and locally verifiable

- [x] Full-year default dataset: 100 contractors, 500 catalog SKUs, daily assigned-position snapshots.
- [x] Reconciliation, usage/inactivity/over-allocation/shortage rules, forecasts and constrained redistribution.
- [x] Transactional imports, visible rejection reports, canonical schemas, stable provenance and duplicate handling.
- [x] Versioned API, pagination, error model, health/readiness, command authorization and idempotency.
- [x] Dark operations UI, evidence drawer, filtered exports, import workflow and architecture page.
- [x] Explicit installed-model picker with no model defaults, local-only verification, schema/citation checks, abstention and deterministic fallback.
- [x] Workplace data-source guide, downloadable validated import example and empty-database first-run imports.
- [x] Weekly persistent job periods and structured request/model telemetry.
- [x] Measured benchmark JSON/CSV/Markdown and independent accounting oracle.
- [x] Backend tests, frontend tests, browser workflow and responsive/accessibility checks.
- [x] Documentation, screenshots, license inventory, contribution and security policies.
- [x] Docker definitions and GitHub Actions workflows committed to the local project.

## Required release gates still external to this local build

- [ ] Execute Docker Compose on a machine with Docker Engine and Compose installed. Docker is absent on the build Mac; a successful native run is not a container verification.
- [ ] Publish to the intended GitHub repository, replace the clone URL and confirm all GitHub Actions jobs pass. No remote CI success is claimed by this local handoff.
- [ ] Review the latest dependency scan, and base-image advisories.
- [ ] Configure private vulnerability reporting and a private conduct-reporting contact.
- [ ] Review model-specific licenses before distributing any weights (none are bundled).
- [ ] Enable branch protection and require backend, frontend, end-to-end, Compose and dependency checks.
- [ ] Make a clean-clone test on Windows and Linux; macOS native verification is recorded locally.
- [ ] Approve the v0.1.0 tag and release notes with the explicit synthetic-data and deployment limitations.

The repository is prepared for public review. This checklist does not assert production readiness or completed external checks.
