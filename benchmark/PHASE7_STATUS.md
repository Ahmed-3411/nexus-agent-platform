# Phase 7 release status

## Completed

- Repaired and locked a mutually compatible FastAPI/Starlette/MCP dependency set.
- Restored the missing authentication routes in the FastAPI application.
- Pinned a Passlib-compatible bcrypt release.
- Aligned PostgreSQL schema and ORM fields, foreign keys, latency, and uniqueness constraints.
- Added an idempotent release migration for existing databases.
- Added database-backed approve/reject recovery tests across simulated restarts.
- Verified sequential approval replay cannot duplicate the tool side effect.
- Restricted CORS to the configured allowlist.
- Ran real orchestration-stack and synthetic benchmarks at concurrency 1, 5, 10, and 25.
- Updated setup, test, benchmark, result, and limitation documentation.

## Final validation

- Full regression command: `.venv/bin/python -m pytest -ra`
- Benchmark command: `.venv/bin/python benchmark/integration_benchmark.py --mode stack --iterations 500 --concurrency 1 5 10 25 --output benchmark/results/release`
- Machine-readable results: `benchmark/results/release/`

## Deployment gates still open

- Apply and smoke-test `backend/db/migrations/001_phase7_release.sql` on the target PostgreSQL deployment.
- Run a deployment benchmark with real LLM and Gmail/Drive/MCP endpoints.
- Add cross-replica idempotency/claiming before promising exactly-once side effects under concurrent approval requests.
- Replace the placeholder frontend if a dashboard is part of the v1 product boundary.
