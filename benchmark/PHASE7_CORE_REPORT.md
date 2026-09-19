# Phase 7 Core Benchmark Report

Date: 2026-09-18

## Scope

This report measures deterministic **in-process control-plane overhead** only: policy evaluation, risk routing, approval decision/resume logic, verification, recovery classification, workflow-state handling, and asyncio scheduling boundaries.

It does **not** include LangGraph runtime, PostgreSQL persistence, MCP transport, Google APIs, Anthropic/LLM latency, network latency, or browser/UI latency. These numbers therefore must not be presented as production end-to-end latency.

## Method

- 4 scenarios: low-risk success, approval path, policy denial, transient recovery.
- Concurrency: 1, 5, 10, 25.
- 10,000 iterations per scenario/concurrency combination.
- 3 independent trials.
- Reported values below are medians across the 3 trials.
- All trials achieved a 100% scenario success rate.

## Key Results

| Scenario | Concurrency | p50 (ms) | p95 (ms) | p99 (ms) | Throughput (ops/s) |
|---|---:|---:|---:|---:|---:|
| Approval | 1 | 0.0063 | 0.0074 | 0.0309 | 60,023 |
| Approval | 5 | 0.0240 | 0.0458 | 0.1275 | 47,695 |
| Approval | 10 | 0.0456 | 0.1265 | 0.4014 | 57,019 |
| Approval | 25 | 0.1139 | 0.2919 | 1.0690 | 58,411 |
| Low risk | 1 | 0.0062 | 0.0072 | 0.0283 | 48,844 |
| Low risk | 5 | 0.0235 | 0.0306 | 0.1134 | 64,098 |
| Low risk | 10 | 0.0447 | 0.0804 | 0.2561 | 54,902 |
| Low risk | 25 | 0.1093 | 0.1877 | 0.6307 | 46,095 |
| Policy denied | 1 | 0.0047 | 0.0056 | 0.0276 | 46,294 |
| Policy denied | 5 | 0.0178 | 0.0234 | 0.0976 | 76,687 |
| Policy denied | 10 | 0.0342 | 0.0623 | 0.2368 | 50,606 |
| Policy denied | 25 | 0.0869 | 0.1973 | 0.4881 | 74,408 |
| Transient recovery | 1 | 0.0053 | 0.0062 | 0.0309 | 58,736 |
| Transient recovery | 5 | 0.0198 | 0.0334 | 0.1457 | 46,736 |
| Transient recovery | 10 | 0.0373 | 0.0659 | 0.2088 | 75,855 |
| Transient recovery | 25 | 0.0919 | 0.1793 | 0.4296 | 42,513 |

## Interpretation

1. The control plane is extremely cheap relative to any realistic external I/O. Typical p50 overhead remains below 0.12 ms even at concurrency 25 in this environment.
2. Approval logic itself is not a meaningful CPU bottleneck. The large real-world cost of an approval workflow will be human wait time and persistence/API round trips, not the decision logic measured here.
3. Tail latency rises with concurrency because the benchmark deliberately introduces an asyncio scheduling boundary. Even so, median p99 remains roughly at or below 1.1 ms for the tested control-plane scenarios.
4. Throughput is intentionally noisy because operations are microsecond-scale and the benchmark is scheduler/OS sensitive. It should be used for regression detection, not capacity planning.
5. The next required benchmark is the full integration run with LangGraph + Postgres + MCP transports + mocked/real provider boundaries. That is the benchmark that can support deployment sizing and end-to-end latency claims.

## Regression Status

In the currently available environment:

- 133 tests passed.
- 2 tests skipped.
- The remaining full-suite collection blockers are unavailable runtime dependencies: `asyncpg`, `python-jose`, and `langgraph` (plus the external MCP SDK/runtime path for the orchestration client).
- Package installation could not be completed because the execution environment cannot reach the package index.

Additional fixes made during Phase 7:

- MCP unit tests now load each server's `tools.py` under a unique module name, eliminating cross-test `sys.modules['tools']` collisions.
- PostgreSQL tool type annotations no longer require `asyncpg` to be importable merely to unit-test the read-only tool logic.
- Benchmark metrics now include group wall time and throughput.
- A dependency-light core benchmark is available at `benchmark/core_benchmark.py`.

## Commands

Core benchmark (no external services):

```bash
python benchmark/core_benchmark.py --iterations 10000 --concurrency 1 5 10 25
```

Full integration benchmark (after installing backend dependencies):

```bash
python benchmark/run_benchmark.py --iterations 100 --concurrency 1 5 10 25
```

Full regression suite:

```bash
pytest -q
```
