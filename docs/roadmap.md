# Next five meaningful improvements

1. **Demand under stockout censoring.** Add intermittent-demand and probabilistic forecasts with service-level calibration, project schedules and genuine unmet-demand observations. Compare against the committed rolling baseline.
2. **Optimization with operational cost.** Use an open-source MILP solver for transfer cost, transit lead times, donor service targets, truck capacities and project priorities. Benchmark feasibility and objective gaps against the greedy allocator.
3. **Real identity and tenant boundaries.** Integrate a locally runnable OpenID Connect provider, scope access by enterprise/market/location, and move persistence to PostgreSQL with tested policies and migrations.
4. **Controlled reconciliation workflow.** Add assigned investigations, count verification, reason-coded corrections and dual approval for posting actual transfers. Preserve a signed audit trail and evaluate idempotency under injected crashes.
5. **Evidence quality and production calibration.** Implement connector contracts, late-arriving event handling, snapshot restatements, lot/serial/UOM conversion and a consented, de-identified field validation dataset. Measure alert usefulness and operator time, not just synthetic precision.

No stretch feature should bypass accounting correctness, field evidence, authorization or model-failure tests.
