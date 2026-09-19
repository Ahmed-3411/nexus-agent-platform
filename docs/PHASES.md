# Delivery Phases

| Phase | Name | Duration (est.) | Deliverable |
|-------|------|------------------|-------------|
| 0 | Architecture & Scaffolding | 1–2 days | repo, docker-compose, DB schema, API skeleton |
| 1 | MCP Servers | 3–5 days | PostgreSQL MCP, Gmail MCP, Drive MCP |
| 2 | LangGraph Orchestration | 3–5 days | Planner, Executor, State, tool calling |
| 3 | Security | 4–7 days | RBAC, Policy Engine, Risk Engine |
| 4 | Verification | 3–5 days | Verification, retry, failure handling, recovery |
| 5 | Human Approval | 2–4 days | Dashboard approval flow |
| 6 | Audit / Observability | 2–4 days | Logs, metrics, workflow traces |
| 7 | Frontend | 5–10 days | Next.js dashboard |
| 8 | Testing | 5–7 days | Unit, integration, adversarial tests |
| 9 | Research | ongoing | Benchmark + ablation experiments |

## Priority order (if time-constrained)

1. MCP
2. LangGraph orchestration
3. Permission / Policy Engine
4. Verification
5. Human approval
6. Auditability
7. Benchmark
8. Dashboard
9. SaaS features

The intelligence and reliability of the system live in the backend — the
dashboard is a thin observability/approval layer on top, not the product
itself.
