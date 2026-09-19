# NEXUS Agent Platform

<p align="center">
  <img src="docs/assets/nexus-hero-auth.png" alt="NEXUS Agent Platform — secure access and platform overview" width="100%" />
</p>

<p align="center">
  <sub>Secure access, governed workflows, platform health, and performance visibility in one workspace.</sub>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-Agent%20Orchestration-1C3C3C?style=flat-square" alt="LangGraph" />
  <img src="https://img.shields.io/badge/MCP-1.28.1-5B5BD6?style=flat-square" alt="Model Context Protocol" />
  <img src="https://img.shields.io/badge/Pydantic-Validation-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic" />
  <img src="https://img.shields.io/badge/Uvicorn-ASGI-499848?style=flat-square" alt="Uvicorn" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL 16" />
  <img src="https://img.shields.io/badge/asyncpg-Async%20Postgres-336791?style=flat-square" alt="asyncpg" />
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis 7" />
  <img src="https://img.shields.io/badge/JWT-Authentication-000000?style=flat-square&logo=jsonwebtokens&logoColor=white" alt="JWT" />
  <img src="https://img.shields.io/badge/SSE-MCP%20Transport-0EA5E9?style=flat-square" alt="SSE Transport" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-Frontend-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/React-UI-61DAFB?style=flat-square&logo=react&logoColor=111827" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-Type%20Safety-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Tailwind%20CSS-Design%20System-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/OpenAI-LLM%20Provider-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Anthropic-LLM%20Provider-191919?style=flat-square&logo=anthropic&logoColor=white" alt="Anthropic" />
  <img src="https://img.shields.io/badge/Gmail-MCP%20Integration-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Gmail" />
  <img src="https://img.shields.io/badge/Google%20Drive-MCP%20Integration-4285F4?style=flat-square&logo=googledrive&logoColor=white" alt="Google Drive" />
  <img src="https://img.shields.io/badge/OAuth%202.0-Google%20Integrations-4285F4?style=flat-square&logo=google&logoColor=white" alt="OAuth 2.0" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Docker-Containers-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Docker%20Compose-Multi--Service%20Runtime-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Compose" />
  <img src="https://img.shields.io/badge/pytest-237%20Passed-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="pytest" />
  <img src="https://img.shields.io/badge/ESLint-Static%20Analysis-4B32C3?style=flat-square&logo=eslint&logoColor=white" alt="ESLint" />
</p>

NEXUS is an **enterprise agentic workflow platform** built to demonstrate end-to-end AI systems engineering rather than a single chatbot or RAG demo.

The project focuses on the engineering problems that appear when LLM planning is connected to real tools and persistent business workflows: authentication, policy enforcement, risk checks, human approval, MCP tool execution, verification, auditability, persistence, failure recovery, graceful provider fallback, and performance measurement.

The repository is intended as a technical portfolio project. The emphasis is on **system design, integration, correctness, failure handling, and observability**.


<p align="center">
  <img src="docs/assets/nexus-overview.png" alt="NEXUS operations dashboard" width="94%" />
</p>

<p align="center">
  <sub>Main operations dashboard for workflow state, approvals, recent activity, and API health.</sub>
</p>

## What this project demonstrates

NEXUS combines a web application, agent orchestration layer, policy engine, persistent workflow state, MCP tool servers, and benchmarking infrastructure into one Dockerized system.

A request can move through the following lifecycle:

```text
User request
   ↓
Authentication / role context
   ↓
Planner
   ↓
Policy + risk evaluation
   ↓
Tool selection
   ↓
Human approval when required
   ↓
MCP execution
   ↓
Result normalization
   ↓
Verification
   ↓
Persistence + audit logging
   ↓
Final workflow result
```

The platform is designed so expected provider or tool failures become **persisted workflow failures**, not unhandled application crashes.

---

## Core engineering capabilities

### Agent orchestration
- Multi-step workflow execution with **LangGraph**
- Planner output normalized into a strict workflow-step schema
- Provider order:
  - Anthropic
  - OpenAI
  - deterministic fallback planner
- Graceful handling of:
  - missing API keys
  - quota exhaustion
  - rate limits
  - provider API failures
  - invalid model output
- Safe fallback behavior that does not invent unsupported tools

### Policy and risk controls
- Tool calls are evaluated before execution
- Role-aware permissions
- Risk classification
- Read-only database execution model
- Explicit SQL safety rules for database queries
- No automatic write/delete execution path
- Human approval support for sensitive actions

### Human-in-the-loop approvals
- Approval records are persisted
- Approve / reject workflow
- Optional decision reason
- Resume from the correct workflow step
- Approval state survives application restart
- Recovery logic avoids duplicate side effects

### MCP integration
The platform uses the **Model Context Protocol (MCP)** for external tool execution.

Implemented MCP services:

| MCP server | Capabilities |
|---|---|
| PostgreSQL | list tables, get schema, describe table, read-only query |
| Gmail | search, read, draft, send |
| Google Drive | search, list, read |

Backend-to-MCP communication uses **SSE transport**.

Logical application tools are mapped to concrete MCP tools, for example:

```text
database.query
    ↓
Postgres MCP
    ↓
query_database(sql: str)
```

Tool results are normalized into structured dictionaries so downstream verification and persistence do not depend on raw MCP return types.

### Persistence and recovery
- PostgreSQL-backed workflow persistence
- Workflow state
- Workflow steps
- Approvals
- Verifications
- Audit logs
- Recovery after restart
- Failed workflows remain inspectable
- Final results and execution errors are persisted

### Verification
Tool results are checked after execution.

Examples:
- database row count is checked against returned rows
- failed MCP calls produce verification evidence with the real failure reason
- verification records are stored for workflow inspection

### Error propagation
The execution layer preserves useful root causes instead of collapsing failures into generic errors.

Examples of handled runtime failures:
- LLM provider quota exhaustion
- missing Gmail credentials
- missing Google Drive credentials
- MCP tool errors
- nested `ExceptionGroup` / `TaskGroup` failures

Secrets and credentials are sanitized before errors are surfaced.

---

# Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         Next.js UI                           │
│  Login • Dashboard • Create • Workflow Detail • Benchmarks  │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP / JWT
┌──────────────────────────────▼───────────────────────────────┐
│                         FastAPI API                          │
│   Auth • Workflow API • Approval API • Health • Persistence │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                     LangGraph Workflow                       │
│                                                              │
│ Planner → Policy/Risk → Executor → Verifier → Finalization  │
│                     ↓                                        │
│               Human Approval                                 │
└──────────────────────────────┬───────────────────────────────┘
                               │ MCP over SSE
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
│ PostgreSQL MCP  │   │   Gmail MCP     │   │   Drive MCP     │
│ FastMCP         │   │   FastMCP       │   │   FastMCP       │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
         │
┌────────▼────────┐
│ PostgreSQL 16   │
└─────────────────┘

Redis is included in the runtime stack for platform infrastructure.
```


<p align="center">
  <img src="docs/assets/nexus-blueprint.png" alt="NEXUS technical blueprint" width="96%" />
</p>

<p align="center">
  <sub>Technical overview of policy-aware execution, persistence, human approval, MCP integrations, health, and benchmarking.</sub>
</p>

---

# Technology stack

## Backend

| Technology | Usage |
|---|---|
| **Python 3.12** | Backend and MCP services |
| **FastAPI** | REST API |
| **Uvicorn** | ASGI server |
| **LangGraph** | Stateful agent workflow orchestration |
| **Pydantic** | Configuration and structured data validation |
| **PostgreSQL 16** | Durable workflow / approval / audit persistence |
| **asyncpg** | Async PostgreSQL access |
| **Redis 7** | Runtime infrastructure |
| **JWT / Bearer auth** | Authenticated API access |
| **Anthropic SDK** | Optional LLM planner provider |
| **OpenAI SDK** | Optional LLM planner provider |
| **pytest** | Regression and integration testing |

## MCP / integrations

| Technology | Usage |
|---|---|
| **Model Context Protocol (MCP)** | Tool boundary between agent runtime and external systems |
| **MCP Python SDK / FastMCP 1.28.1** | MCP servers |
| **SSE transport** | Backend ↔ MCP communication |
| **Google OAuth** | Gmail / Drive integration |
| **PostgreSQL MCP tools** | Database inspection and safe read queries |

## Engineering Stack

| Area | Technologies / Tools |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn, LangGraph, Pydantic |
| LLM Providers | OpenAI SDK, Anthropic SDK |
| MCP | Model Context Protocol, MCP Python SDK, FastMCP 1.28.1, SSE |
| Data & Persistence | PostgreSQL 16, asyncpg, Redis 7 |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Authentication & Access | JWT / Bearer auth, role-based permissions |
| External Integrations | Gmail API, Google Drive API, Google OAuth 2.0 |
| Testing | pytest, integration tests, MCP contract tests, TypeScript validation, ESLint |
| Performance | p50 / p95 / p99, throughput, success rate, concurrency testing |
| Infrastructure | Docker, Docker Compose, multi-container networking |

## Key Engineering Features

- Policy-aware tool execution
- Human-in-the-loop approvals
- Persistent workflow recovery
- Structured verification
- Root-cause error propagation
- Safe read-only SQL execution
- Secret sanitization
- Real-stack and synthetic benchmark separation

---

# Frontend

<p align="center">
  <img src="docs/assets/nexus-suite.png" alt="NEXUS product suite views" width="96%" />
</p>

<p align="center">
  <sub>Overview, health, and benchmark views presented as a single product suite.</sub>
</p>


| Technology | Usage |
|---|---|
| **Next.js** | Web application |
| **React** | UI components |
| **TypeScript** | Type-safe frontend |
| **Tailwind CSS** | Design system and responsive styling |
| **Next.js API proxy** | Backend request proxying |
| **JWT client flow** | Authenticated workflow UI |

## Infrastructure and delivery

| Technology | Usage |
|---|---|
| **Docker** | Service packaging |
| **Docker Compose** | Local multi-service orchestration |
| **PostgreSQL container** | Database service |
| **Redis container** | Runtime service |
| **Separate MCP containers** | Postgres, Gmail, Drive servers |
| **Environment-based configuration** | Secrets and service URLs |
| **`.env.example`** | Safe configuration template |

## Validation and performance

| Technology / method | Usage |
|---|---|
| **pytest** | Backend regression suite |
| **TypeScript compiler** | Frontend type validation |
| **ESLint** | Frontend static analysis |
| **Next.js production build** | Production frontend validation |
| **Phase 7 benchmark harness** | Latency / throughput testing |
| **p50 / p95 / p99 / mean** | Latency statistics |
| **Concurrency 1, 5, 10, 25** | Scaling behavior |
| **Real-stack vs synthetic modes** | Separates measured execution from modeled latency |

---

# Frontend

The frontend is not only a control surface for demos. It exposes the important internal workflow state so execution can be inspected.

Implemented pages include:

- Login
- Registration
- Dashboard
- Create Workflow
- Workflow Details
- System Health
- Benchmark Results

The workflow detail page exposes:
- request
- role
- status
- current step
- plan
- tool arguments
- result
- error
- risk level
- verification
- approvals
- final result

This makes the platform useful for debugging and explaining agent behavior instead of hiding execution behind a chat interface.

---

# Workflow execution example

A simple request:

```text
List database tables
```

can produce a planned step:

```json
{
  "step_index": 0,
  "tool_name": "database.list_tables",
  "arguments": {},
  "description": "List available public database tables."
}
```

A successful MCP response is normalized:

```json
{
  "tables": [
    "approvals",
    "audit_logs",
    "organizations",
    "permissions",
    "role_permissions",
    "roles",
    "tools",
    "users",
    "verifications",
    "workflow_steps",
    "workflows"
  ],
  "ok": true,
  "tool_name": "list_tables",
  "server": "postgres"
}
```

The result is then verified and persisted.

---

# Safe SQL execution

`database.query` does not accept arbitrary natural-language requests as SQL.

The deterministic fallback only uses `database.query` when the request already contains valid read-only SQL.

Allowed query forms are restricted to read operations such as:

```sql
SELECT 1 AS value;
```

Example result:

```json
{
  "row_count": 1,
  "truncated": false,
  "rows": [
    {
      "value": 1
    }
  ],
  "ok": true,
  "tool_name": "query_database",
  "server": "postgres"
}
```

The verification layer checks:

```text
row_count == len(rows)
```

Write and delete operations are intentionally not exposed as executable database tools.

---

# Failure behavior

A key design goal is to make failures inspectable.

For example, running Drive without OAuth credentials returns a structured tool failure instead of crashing the API:

```json
{
  "ok": false,
  "error": "Drive credentials are not configured.",
  "tool_name": "search_files",
  "server": "drive"
}
```

The workflow becomes `FAILED`, while:
- the workflow remains persisted
- the step error is stored
- verification is recorded
- the final result contains the root cause
- the workflow details API remains usable

The same behavior is implemented for Gmail credential failures.

---

# System health

<p align="center">
  <img src="docs/assets/nexus-health.png" alt="NEXUS system health page" width="94%" />
</p>

<p align="center">
  <sub>Live core API status, round-trip timing, and health-check scope.</sub>
</p>


The health UI surfaces:
- core API availability
- browser-to-API round trip
- last checked time
- scope of the health check

External LLM, Gmail, Drive, and database-provider availability are validated when their workflow tools run.

---

# Benchmarking

<p align="center">
  <img src="docs/assets/nexus-benchmarks.png" alt="NEXUS benchmark page" width="94%" />
</p>

<p align="center">
  <sub>Measured latency, throughput, and concurrency behavior across real-stack benchmark scenarios.</sub>
</p>


The benchmark infrastructure measures:

- p50 latency
- p95 latency
- p99 latency
- mean latency
- throughput
- success rate
- concurrency levels `1`, `5`, `10`, `25`

Scenarios include:
- policy-denied path
- normal read/tool path
- approval workflow path

The benchmark page explicitly separates:
- **real-stack measurements**
- **synthetic latency-budget simulations**

Example measured result for the normal read/tool scenario at concurrency 25:

| Metric | Result |
|---|---:|
| p50 | 111.71 ms |
| p95 | 222.13 ms |
| p99 | 239.27 ms |
| mean | 123.17 ms |
| throughput | 192.5 ops/s |
| success rate | 100% |

These numbers represent the tested orchestration stack, not external LLM-provider latency.

---

# Testing status

Current validated state:

```text
Backend regression suite: 237 passed
Frontend npm install: passed
TypeScript validation: passed
ESLint: passed
Next.js production build: passed
All application routes generated successfully
```

Runtime smoke tests also validated:

```text
database.list_tables   ✓
database.get_schema    ✓
database.query         ✓
Drive missing OAuth    ✓ clean failure
Gmail missing OAuth    ✓ clean failure
LLM unavailable        ✓ deterministic fallback
MCP SSE transport      ✓
Workflow persistence   ✓
Verification records   ✓
Audit logs             ✓
```

---

# Docker services

The local stack contains:

```text
frontend       :3000
backend        :8000
mcp-postgres   :9101
mcp-gmail      :9102
mcp-drive      :9103
postgres       :5432
redis          :6379
```

MCP endpoints used by the backend:

```text
http://mcp-postgres:9101/sse
http://mcp-gmail:9102/sse
http://mcp-drive:9103/sse
```

---

# Running locally

## 1. Clone

```bash
git clone <your-repository-url>
cd <repository-directory>
```

## 2. Create local environment file

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

The project can run without Anthropic or OpenAI credentials because the planner has a deterministic fallback.

Gmail and Drive require Google OAuth credentials for real external calls.

## 3. Start the stack

```bash
docker compose up -d --build
```

## 4. Check services

```bash
docker compose ps
```

## 5. Open

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
API docs: http://localhost:8000/docs
```

---

# Environment configuration

Example configuration:

```env
POSTGRES_USER=eap
POSTGRES_PASSWORD=eap_dev_password
POSTGRES_DB=eap
DATABASE_URL=postgresql+asyncpg://eap:eap_dev_password@postgres:5432/eap

REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=change_me_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5

OPENAI_API_KEY=
OPENAI_MODEL=

MCP_POSTGRES_URL=http://mcp-postgres:9101/sse
MCP_GMAIL_URL=http://mcp-gmail:9102/sse
MCP_DRIVE_URL=http://mcp-drive:9103/sse

GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=

DRIVE_CLIENT_ID=
DRIVE_CLIENT_SECRET=
DRIVE_REFRESH_TOKEN=

ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

Never commit the real `.env` file.

---

# Repository structure

```text
.
├── backend/
│   ├── agents/
│   │   ├── planner.py
│   │   ├── graph.py
│   │   ├── executor.py
│   │   ├── verifier.py
│   │   ├── recovery.py
│   │   ├── mcp_client.py
│   │   ├── tool_catalog.py
│   │   └── sql_safety.py
│   ├── api/
│   ├── core/
│   └── db/
│
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
│
├── mcp/
│   ├── postgres/
│   ├── gmail/
│   └── drive/
│
├── benchmark/
├── tests/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# Engineering decisions

## Why MCP?
The project treats external systems as explicit tool boundaries instead of embedding provider-specific logic directly in the agent graph.

This makes the execution layer easier to inspect, replace, and secure.

## Why persist failures?
A failed business workflow is still useful operational data.

Persisting failed workflows allows:
- debugging
- auditability
- retry analysis
- user-facing error inspection
- post-restart recovery

## Why deterministic fallback?
An orchestration platform should not return HTTP 500 only because an LLM provider is unavailable.

The deterministic fallback keeps supported read-only workflows usable and makes provider failure a degraded mode instead of total application failure.

## Why human approval?
Some tool actions should not be treated like ordinary function calls.

Approval is modeled as persistent workflow state so the application can stop, restart, and resume safely.

## Why separate real and synthetic benchmarks?
Modeled latency budgets are useful, but they are not measurements.

The benchmark UI and data model keep synthetic simulation separate from real orchestration-stack results.

---


# Current limitations

This repository is a strong local / portfolio / demo implementation, not a finished multi-tenant production SaaS.

Known areas for further production hardening include:

- distributed approval claiming across replicas
- stronger cross-replica idempotency guarantees
- MCP connection pooling
- JWT revocation / session invalidation
- full tenant-isolation enforcement
- distributed tracing
- production migration strategy
- live provider benchmarks including external LLM latency
- production OAuth secret management
- deployment automation and infrastructure-as-code

These are intentionally documented instead of hidden because they define the next engineering boundary of the platform.

---


---

## License

See [`LICENSE`](LICENSE).
