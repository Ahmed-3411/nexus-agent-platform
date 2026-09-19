"""
Workflow runner.

Owns the compiled graphs and an in-memory workflow store, and exposes the
three operations the API layer needs:

  - start_workflow(user_request, role, user_id=None, db=None)  -> run a
    fresh workflow to completion (which may mean SUCCEEDED, FAILED, or
    paused at AWAITING_APPROVAL — see agents/graph.py's routing).
  - approve_step(workflow_id, approve, db=None)  -> resume a paused
    workflow after a human decision, re-entering the graph at risk_check
    rather than replanning from scratch (see build_resume_graph()'s
    docstring).
  - get_workflow(workflow_id)  -> read-only in-memory lookup for GET
    /workflows/{id}. Does NOT fall back to the database itself — see
    db/workflow_repository.load_workflow_state() and api/workflows.py,
    which call that directly when this returns None.

The in-memory `_workflow_store` dict is still the source of truth within
one running API process (both for speed and because it's what
approve_step() reads from). `db` is optional and additive: when the
caller passes a real AsyncSession, every run is also durably persisted
via db/workflow_repository.save_workflow_state() and its audit trail via
audit/logger.persist_audit_entries() — both of which need the workflow
row to exist first, which save_workflow_state() itself creates. Callers
that don't pass `db` (including all of this module's own unit tests)
get the exact Phase 5/6 behavior: in-memory only, audit trail only as
log lines via log_audit_entries().
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from agents.graph import build_graph, build_resume_graph
from agents.state import WorkflowState, new_workflow_state
from audit.logger import log_audit_entries, persist_audit_entries

_graph = build_graph()
_resume_graph = build_resume_graph()

_workflow_store: dict[str, WorkflowState] = {}


class WorkflowNotFoundError(KeyError):
    pass


class WorkflowNotAwaitingApprovalError(ValueError):
    pass


async def _record_run(workflow_id: str, user_id: str | None, state: WorkflowState, db: AsyncSession | None) -> None:
    """Emit the audit trail, and persist to Postgres too if a session was given."""
    now = datetime.now(timezone.utc)
    state.setdefault("created_at", now)
    state["updated_at"] = now
    log_audit_entries(workflow_id, state)
    if db is not None:
        # Keep the persistence dependency at the boundary used by DB-backed runs.
        from db.workflow_repository import save_workflow_state

        await save_workflow_state(db, workflow_id, user_id, state)
        await persist_audit_entries(db, workflow_id, state)


async def start_workflow(
    user_request: str, role: str, *, user_id: str | None = None, db: AsyncSession | None = None
) -> tuple[str, WorkflowState]:
    """Run a brand-new workflow to completion and store its final state."""
    workflow_id = str(uuid.uuid4())
    initial_state = new_workflow_state(user_request, role=role)
    final_state = await _graph.ainvoke(initial_state)
    _workflow_store[workflow_id] = final_state
    await _record_run(workflow_id, user_id, final_state, db)
    return workflow_id, final_state


async def approve_step(
    workflow_id: str,
    approve: bool,
    *,
    user_id: str | None = None,
    db: AsyncSession | None = None,
    reason: str | None = None,
) -> WorkflowState:
    """
    Resolve the pending approval on a paused workflow.

    If rejected, the run ends as FAILED with the rejection recorded — no
    resume graph run happens. If approved, the current step index is
    added to `approved_steps` and the resume graph re-enters at
    risk_check, which will now let that step through to execution.
    """
    state = _workflow_store.get(workflow_id)
    if state is None and db is not None:
        from db.workflow_repository import load_workflow_execution_state

        state = await load_workflow_execution_state(db, workflow_id)
        if state is not None:
            _workflow_store[workflow_id] = state
    if state is None:
        raise WorkflowNotFoundError(f"No workflow found with id '{workflow_id}'.")
    if state["status"] != "AWAITING_APPROVAL":
        raise WorkflowNotAwaitingApprovalError(
            f"Workflow '{workflow_id}' is not awaiting approval (status={state['status']})."
        )

    idx = state["current_step_index"]

    approval_id = None
    if db is not None:
        from db.workflow_repository import record_approval_decision

        approval_id = await record_approval_decision(
            db, workflow_id, idx, user_id, approve, reason=reason
        )

    approval_records = dict(state.get("approvals", {}))
    approval_records[idx] = {
        "id": str(approval_id) if approval_id else None,
        "decision": "APPROVED" if approve else "REJECTED",
        "reason": reason,
        "decided_by": user_id,
    }

    if not approve:
        rejected_state = dict(state)
        rejection_error = f"Step {idx} was rejected by a human reviewer."
        rejected_errors = dict(state.get("errors", {}))
        rejected_errors[idx] = rejection_error
        rejected_state["errors"] = rejected_errors
        rejected_state["approvals"] = approval_records
        rejected_state["status"] = "FAILED"
        rejected_state["final_result"] = {"error": rejection_error}
        _workflow_store[workflow_id] = rejected_state
        await _record_run(workflow_id, user_id, rejected_state, db)
        return rejected_state

    approved_steps = set(state.get("approved_steps", set()))
    approved_steps.add(idx)
    resumed_state = dict(state)
    resumed_state["approved_steps"] = approved_steps
    resumed_state["approvals"] = approval_records
    resumed_state["status"] = "RUNNING"

    final_state = await _resume_graph.ainvoke(resumed_state)
    _workflow_store[workflow_id] = final_state
    await _record_run(workflow_id, user_id, final_state, db)
    return final_state


def get_workflow(workflow_id: str) -> WorkflowState | None:
    return _workflow_store.get(workflow_id)
