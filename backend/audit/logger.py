"""
Audit trail: turns a finished WorkflowState into a list of audit log
entries (one per plan step that was actually reached), and emits them.

Two emission paths are available:

  - `log_audit_entries()` writes structured log lines via the standard
    `logging` module. This works right now, with no database required,
    and is what `agents/runner.py` calls after every run. This is the
    "Observability" half of the original brief's Phase 6.
  - `persist_audit_entries()` writes rows into `audit_logs` after workflow
    persistence has created the referenced workflow and step rows.

`build_audit_entries()` itself is pure and fully unit-testable without
any database or logging setup.
"""
import json
import logging
from typing import Any, TypedDict

from agents.state import WorkflowState
from policies.permission_map import required_permission_or_none

logger = logging.getLogger("eap.audit")


class AuditEntry(TypedDict):
    workflow_id: str
    step_index: int
    tool_name: str
    arguments: dict[str, Any]
    permission_code: str | None
    risk_level: str | None
    result: str  # SUCCESS / FAILURE / DENIED
    latency_ms: int | None
    error: str | None


def _classify_result(step_index: int, state: WorkflowState) -> tuple[str, str | None]:
    """Return (result, error) for one step based on the final state."""
    error = state.get("errors", {}).get(step_index)
    has_result = step_index in state.get("results", {})

    if has_result and error is None:
        return "SUCCESS", None
    if error is not None and error.startswith("Policy denied"):
        return "DENIED", error
    if error is not None:
        return "FAILURE", error
    # Reached risk_check (so it has a risk_level) but never got to
    # execute (e.g. the run ended while still AWAITING_APPROVAL).
    return "PENDING", None


def build_audit_entries(workflow_id: str, state: WorkflowState) -> list[AuditEntry]:
    """
    Build one AuditEntry per plan step that risk_check_node reached
    (i.e. has an entry in `risk_levels`), covering steps that succeeded,
    failed, were denied by policy, or are still pending approval.
    """
    entries: list[AuditEntry] = []
    risk_levels = state.get("risk_levels", {})
    plan_by_index = {step["step_index"]: step for step in state.get("plan", [])}

    for step_index, risk_level in sorted(risk_levels.items()):
        step = plan_by_index.get(step_index)
        if step is None:
            continue
        result, error = _classify_result(step_index, state)
        entries.append(
            AuditEntry(
                workflow_id=workflow_id,
                step_index=step_index,
                tool_name=step["tool_name"],
                arguments=step.get("arguments", {}),
                permission_code=required_permission_or_none(step["tool_name"]),
                risk_level=risk_level,
                result=result,
                latency_ms=state.get("step_latency_ms", {}).get(step_index),
                error=error,
            )
        )
    return entries


def log_audit_entries(workflow_id: str, state: WorkflowState) -> list[AuditEntry]:
    """
    Build and emit audit entries as structured log lines. Returns the
    entries too, so callers (and tests) can inspect what was logged
    without needing a log-capture fixture.
    """
    entries = build_audit_entries(workflow_id, state)
    for entry in entries:
        logger.info("audit_entry %s", json.dumps(entry, default=str))
    return entries


async def persist_audit_entries(db, workflow_id: str, state: WorkflowState) -> None:
    """Write audit entries linked to the persisted workflow and step rows."""
    import uuid

    from sqlalchemy import select

    from db.models import AuditLog, WorkflowStep

    entries = build_audit_entries(workflow_id, state)
    workflow_uuid = uuid.UUID(workflow_id)
    result = await db.execute(
        select(WorkflowStep.step_index, WorkflowStep.id).where(
            WorkflowStep.workflow_id == workflow_uuid
        )
    )
    step_ids = {step_index: step_id for step_index, step_id in result.all()}
    for entry in entries:
        db.add(
            AuditLog(
                workflow_id=workflow_uuid,
                workflow_step_id=step_ids.get(entry["step_index"]),
                tool_name=entry["tool_name"],
                arguments=entry["arguments"],
                permission_code=entry["permission_code"],
                risk_level=entry["risk_level"],
                result=entry["result"],
                latency_ms=entry["latency_ms"],
                error=entry["error"],
            )
        )
    await db.commit()
