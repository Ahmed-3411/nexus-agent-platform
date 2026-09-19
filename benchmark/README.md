# Phase 7 benchmark

`integration_benchmark.py` keeps measured stack behavior and synthetic latency-budget simulation separate.

## Real orchestration stack

This mode executes the installed LangGraph graph, policy and risk gates, verifier, recovery, approval pause/resume flow, and runner. Planner and external MCP calls are deterministic boundaries so the measurement isolates the platform control plane.

```bash
.venv/bin/python benchmark/integration_benchmark.py \
  --mode stack --iterations 500 --concurrency 1 5 10 25 \
  --output benchmark/results/release
```

Scenarios:

- `denied_path`: unauthorized send is rejected before execution.
- `read_path`: allowed read/tool step executes and verifies.
- `approval_path`: send pauses, is approved, resumes without replanning, and verifies.

Every scenario/concurrency group reports sample count, success rate, mean, p50, p95, p99, and throughput. The command exits non-zero when a scenario's success rate is below 100%.

## Synthetic simulation

This mode validates timing attribution and concurrency accounting only. Its numbers are never production or real-stack results.

```bash
.venv/bin/python benchmark/integration_benchmark.py \
  --mode synthetic --iterations 500 --concurrency 1 5 10 25 \
  --output benchmark/results/release
```

Outputs use distinct names:

- `integration_stack_{raw.csv,summary.csv,summary.json}`
- `integration_synthetic_{raw.csv,summary.csv,summary.json}`

## Additional regression benchmark

`run_benchmark.py` is the earlier deterministic orchestration regression harness. `core_benchmark.py` measures only dependency-light policy/risk/approval/verification/recovery functions. Neither replaces a live deployment benchmark with real provider credentials.
