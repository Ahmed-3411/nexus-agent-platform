# Enterprise Agentic Workflow Platform

A security-first Python platform for planning and executing multi-step enterprise workflows through MCP services. It includes JWT authentication, RBAC, fail-closed policy enforcement, risk-based human approval, post-action verification, recovery, durable workflow state, and append-only audit records.

## Release status

The backend/control-plane release candidate and Next.js operations dashboard are complete. The repository has not been benchmarked against live Gmail/Drive/provider endpoints; see [Known limitations](#known-limitations).

## Architecture

The FastAPI service authenticates callers and passes the signed role claim into a LangGraph workflow. Every planned tool call passes through policy and risk gates before the MCP client can execute it. High-risk actions pause for a persisted human decision. Workflow steps, approvals, verifications, latency, and audit records are stored in PostgreSQL so a paused workflow can be restored after an application restart.

Main components:

- `backend/api/`: authentication, health, workflow, approve, and reject endpoints.
- `backend/agents/`: planner, graph, executor, verifier, recovery, runner, and MCP client.
- `backend/policies/` and `backend/risk/`: RBAC and approval routing.
- `backend/db/`: PostgreSQL models, bootstrap schema, persistence, and release migration.
- `mcp/`: read-only PostgreSQL, Gmail, and Google Drive MCP services; Gmail also exposes draft/send with upstream approval enforcement.
- `tests/`: unit, benchmark-harness, and database-backed approval-recovery tests.
- `benchmark/`: deterministic synthetic and real orchestration-stack benchmark modes.
- `frontend/`: Next.js dashboard for authentication, workflow operations, approvals, health, and benchmark results.

## Setup

Python 3.12 is the supported runtime.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  -r backend/requirements.txt \
  -r mcp/postgres/requirements.txt \
  -r mcp/gmail/requirements.txt \
  -r mcp/drive/requirements.txt \
  -r tests/requirements.txt
python -m pip check
```

Configure the application:

```bash
cp .env.example .env
```

Replace `JWT_SECRET_KEY`, add only the provider credentials you use, and set `CORS_ORIGINS` to a comma-separated allowlist. Never use the example JWT secret in production.

For a fresh Docker-based database and services:

```bash
docker compose up -d --build
```

`backend/db/schema.sql` is applied automatically only when the PostgreSQL volume is first initialized. For a database created from an earlier repository version, run:

```bash
psql "$DATABASE_URL" -f backend/db/migrations/001_phase7_release.sql
```

When `DATABASE_URL` uses SQLAlchemy's `postgresql+asyncpg://` prefix, use an equivalent `postgresql://` URL with `psql`.

Run the API without Docker after starting PostgreSQL:

```bash
cd backend
../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`.

Frontend: `http://localhost:3000`. The Docker service proxies API requests to
the backend container, so the browser only needs access to port 3000.

## Tests

Run the complete suite from the repository root:

```bash
.venv/bin/python -m pytest -ra
```

The approval recovery integration test uses an on-disk relational database, disposes all connections, clears the process cache, reopens the database, then validates both approve and reject recovery. It also verifies that replaying an approval after another restart does not execute the tool side effect twice.

## Benchmarks

Real orchestration-stack benchmark (real LangGraph, policy, risk, approval, verification, and recovery code; deterministic planner/MCP boundaries):

```bash
.venv/bin/python benchmark/integration_benchmark.py \
  --mode stack --iterations 500 --concurrency 1 5 10 25 \
  --output benchmark/results/release
```

Synthetic latency-budget validation, reported separately and never as real performance:

```bash
.venv/bin/python benchmark/integration_benchmark.py \
  --mode synthetic --iterations 500 --concurrency 1 5 10 25 \
  --output benchmark/results/release
```

The release run is documented in `benchmark/PHASE7_INTEGRATION_REPORT.md`; machine-readable CSV/JSON and raw samples are under `benchmark/results/release/`.

## Release benchmark summary

Each cell is `p50 / p95 / p99 / mean ms | throughput ops/s`; every group contains 500 samples and achieved 100% scenario success.

| Scenario | C=1 | C=5 | C=10 | C=25 |
| --- | --- | --- | --- | --- |
| Policy denied | 3.700 / 4.754 / 6.308 / 3.873 \| 256.25 | 13.953 / 17.537 / 22.219 / 14.183 \| 332.20 | 24.684 / 31.366 / 95.850 / 25.643 \| 353.84 | 66.136 / 167.475 / 177.683 / 75.082 \| 303.45 |
| Normal read/tool | 5.899 / 8.146 / 10.071 / 6.343 \| 110.15 | 24.993 / 35.143 / 99.391 / 26.794 \| 177.64 | 44.587 / 64.380 / 132.761 / 47.485 \| 199.12 | 111.712 / 222.131 / 239.270 / 123.166 \| 192.52 |
| Approval workflow | 7.933 / 11.024 / 14.388 / 8.376 \| 118.94 | 34.069 / 44.235 / 57.574 / 35.422 \| 137.83 | 62.632 / 80.497 / 172.145 / 66.539 \| 146.03 | 160.468 / 300.220 / 338.000 / 172.339 \| 140.42 |

The main observed bottleneck is orchestration/event-loop contention under higher concurrency. Throughput plateaus by concurrency 10 and tail latency grows sharply at 25; approval is the most expensive path because it invokes two graph runs.

## Known limitations

- Stack-mode numbers measure the real control plane with deterministic planner and MCP boundaries. They do not include live LLM, network, SaaS, or provider throttling latency.
- The recovery test validates durable semantics with SQLite for portability. PostgreSQL remains the production database, and the release migration must still be exercised in the target deployment.
- Gmail/Drive OAuth credentials and live provider behavior are environment-specific and were not exercised in the release benchmark.
- Role changes take effect when a new JWT is issued; there is no token revocation/blocklist.
- Exactly-once execution is protected against sequential approval replay after recovery, but cross-replica concurrent approval requires an external idempotency key or distributed execution claim at the tool boundary.
- The MCP client opens a new SSE session per tool call; production connection pooling is not implemented.
- Metrics export and distributed tracing are not included; audit logs and per-step latency are available.
- Multi-tenancy/organization enforcement is not implemented.

## License

MIT; see `LICENSE`.
