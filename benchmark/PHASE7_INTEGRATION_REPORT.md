# Phase 7 release benchmark report

Run date: 2026-09-18. Runtime: CPython 3.12.14 on Linux. Each scenario/concurrency group contains 500 samples.

## Real orchestration-stack results

Command:

```bash
.venv/bin/python benchmark/integration_benchmark.py \
  --mode stack --iterations 500 --concurrency 1 5 10 25 \
  --output benchmark/results/release
```

This is measured execution of the installed LangGraph orchestration, policy, risk, approval, verification, recovery, and runner code. Planner and MCP/provider boundaries are deterministic, so these results measure control-plane overhead rather than external network or provider latency.

| Scenario | Concurrency | Mean ms | p50 ms | p95 ms | p99 ms | Throughput ops/s | Success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Approval | 1 | 8.376 | 7.933 | 11.024 | 14.388 | 118.94 | 100% |
| Approval | 5 | 35.422 | 34.069 | 44.235 | 57.574 | 137.83 | 100% |
| Approval | 10 | 66.539 | 62.632 | 80.497 | 172.145 | 146.03 | 100% |
| Approval | 25 | 172.339 | 160.468 | 300.220 | 338.000 | 140.42 | 100% |
| Policy denied | 1 | 3.873 | 3.700 | 4.754 | 6.308 | 256.25 | 100% |
| Policy denied | 5 | 14.183 | 13.953 | 17.537 | 22.219 | 332.20 | 100% |
| Policy denied | 10 | 25.643 | 24.684 | 31.366 | 95.850 | 353.84 | 100% |
| Policy denied | 25 | 75.082 | 66.136 | 167.475 | 177.683 | 303.45 | 100% |
| Read/tool | 1 | 6.343 | 5.899 | 8.146 | 10.071 | 110.15 | 100% |
| Read/tool | 5 | 26.794 | 24.993 | 35.143 | 99.391 | 177.64 | 100% |
| Read/tool | 10 | 47.485 | 44.587 | 64.380 | 132.761 | 199.12 | 100% |
| Read/tool | 25 | 123.166 | 111.712 | 222.131 | 239.270 | 192.52 | 100% |

Main bottleneck: control-plane/event-loop contention. Throughput plateaus at concurrency 10 and p95/p99 rise materially at concurrency 25. Approval is the slowest route because it performs a pause and a second graph invocation to resume.

## Synthetic results (separate)

Command:

```bash
.venv/bin/python benchmark/integration_benchmark.py \
  --mode synthetic --iterations 500 --concurrency 1 5 10 25 \
  --output benchmark/results/release
```

All synthetic groups achieved 100% accounting success. Across concurrency 1–25, synthetic p50 was 3.276–3.765 ms for denied, 23.849–24.899 ms for read/tool, and 36.216–37.439 ms for approval. These are configured latency-budget simulations and are not real performance results.

## Approval recovery validation

`tests/integration/test_approval_recovery.py` validates both decisions across a simulated application restart:

1. Persist a paused approval and close the database connection.
2. Clear the process-local workflow cache and reopen the database.
3. Rehydrate the exact step and approve or reject it.
4. Verify the decision and final step state were persisted.
5. For approval, simulate another restart and replay; the side-effecting tool remains called exactly once.

## Scope boundary

The execution environment did not provide usable Docker or a runnable non-root PostgreSQL daemon, and no live Gmail/Drive/provider credentials were supplied. The durable recovery integration uses SQLite for portable relational validation. Production PostgreSQL, live OAuth providers, and real LLM/MCP network latency remain deployment validation items and are not represented by the table above.
