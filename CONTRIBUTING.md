# Contributing

Contributions should improve a real inventory-control decision and include evidence that the change works. Open an issue explaining the operational case, expected behavior and constraints before a large redesign.

1. Follow the native setup in the README and create a feature branch.
2. Keep accounting and forecasting in `packages/consignai/domain`, persistence in `data`, orchestration in `services`, and display logic in `apps/web`.
3. Add regression tests for accounting, validation, authorization or model-boundary changes. Use fixed seeds and never require paid services.
4. Run `ruff check packages apps/api tests scripts`, `ruff format --check packages apps/api tests scripts`, `pytest`, and the small benchmark. In `apps/web`, run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` and `pnpm e2e`.
5. Update API schemas, ADRs, data dictionary and measured results if behavior changes. Do not rewrite benchmark claims without rerunning the harness and naming the configuration.
6. Include the problem, before/after behavior, validation and limitations in the PR. Avoid generated credentials and private customer data.

Code is Apache-2.0. By submitting a contribution, you confirm you have the right to license it under the project license. Human review is required for release. Security reports follow SECURITY.md.
