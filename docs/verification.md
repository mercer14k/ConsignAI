# Local verification record

Build environment: macOS 26.6.2, arm64, Python 3.12.14. The application was exercised against the complete seed-42 synthetic dataset. This file distinguishes executed checks from configured future checks.

## Executed successfully

- Backend: **49 pytest tests passed**, covering deterministic rules, schemas, database/API workflow, missing evidence, AI failures, cross-owner boundaries, transfer conservation, upload limits, origin rejection the evaluation harness, explicit per-request model selection, local model discovery/filtering, and the ten-record workplace import example.
- Coverage: **86% overall**, **99% domain engine**, **98% analysis service** in the earlier 33-test coverage run (before the model picker change); coverage was not remeasured for the 49-test run. The CLI is exercised manually rather than covered by that pytest run.
- Backend lint and formatting checks pass.
- Frontend: **eight component tests passed**, TypeScript check, ESLint and production build pass.
- Browser: **five Playwright tests passed** against the real API: investigation/explanation/export/rerun, malformed upload with unchanged ledger, redistribution/mobile layout, desktop overview accessibility, and explicit model selection/clearing/reset on reload. Discovery is stubbed in the selection regression; its explanation request exercises the real API and a nonexistent model must visibly fall back. Other workflow calls use the real full-year API.
- Desktop overview and local-model picker: no serious or critical axe-core findings in the tested states. Mobile overview: no document-width overflow at 390 × 844.
- Dependency audits: no reported Python or npm advisories after patching dependencies. These are point-in-time advisory scans, not a security guarantee or container scan.
- Backend wheel built and checked for packaged API/domain modules.
- Generator, small-fixture import and full-year benchmark executed; actual outputs are committed.
- Canonical architecture JSON validated against its schema and statically linted with the Mermaid authoring tool. GitHub rendering was not exercised.

An explicitly tested Qwen2.5 1.5B local runtime produced a schema-valid **abstention** in the committed smoke test. That demonstrates the runtime/validation path, not successful unrestricted narrative quality. Earlier rejected model responses are retained as separate failure evidence. All deterministic functionality passed with no model selected. The running local API discovered the device's installed `qwen3:8b` model during the picker check; discovery did not load or run it. The app did not preselect it.

## Explicitly not verified here

- Docker Compose startup: no Docker installation on the build Mac.
- GitHub Actions execution: this delivery is local; no remote repository/CI run is claimed.
- Native Windows/Linux, organizational SSO/tenant deployment, external connectors, container-image vulnerability scan and field-data accuracy.

See the machine-readable benchmark, model smoke tests and release checklist for their respective scopes. Passing local tests does not turn a reference implementation into a production deployment certification.
