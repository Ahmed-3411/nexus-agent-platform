"""
Persistence for workflow runs and human approvals.

A workflow is persisted after every start/resume operation. When a run
pauses at ``AWAITING_APPROVAL`` this module also ensures a pending
``approvals`` row exists for the current step. Approval decisions are
recorded separately before execution resumes, preserving who decided,
when, and an optional reason.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agents.state import WorkflowState
from db.models import Approval, Verification, Workflow, WorkflowStep


def _step_status(step_index: int, state: WorkflowState) -> str:
    """Classify one step's persisted status from the workflow state."""
    if step_index in state.get("results", {}) and step_index not in state.get("errors", {}):
        return "SUCCEEDED"
    if step_index in state.get("errors", {}):
        return "FAILED"
    if state.get("status") == "AWAITING_APPROVAL" and state.get("current_step_index") == step_index:
        return "AWAITING_APPROVAL"
    return "PENDING"


def _current_step_index_from_steps(status: str, steps: list[dict[str, Any]]) -> int:
    """Recover the graph cursor from persisted step rows."""
    if status == "AWAITING_APPROVAL":
        for step in steps:
            if step.get("status") == "AWAITING_APPROVAL":
                return int(step["step_index"])
    pending = [int(s["step_index"]) for s in steps if s.get("status") == "PENDING"]
    if pending:
        return min(pending)
    return max((int(s["step_index"]) for s in steps), default=-1) + 1


async def _ensure_pending_approval(db: AsyncSession, step_row: WorkflowStep) -> Approval:
    """Return the existing pending approval for a step, or create it once."""
    result = await db.execute(
        select(Approval)
        .where(Approval.workflow_step_id == step_row.id, Approval.decision.is_(None))
        .order_by(Approval.requested_at.desc())
        .limit(1)
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        approval = Approval(workflow_step_id=step_row.id)
        db.add(approval)
        await db.flush()
    return approval


async def save_workflow_state(
    db: AsyncSession, workflow_id: str, user_id: str | None, state: WorkflowState
) -> None:
    """Upsert workflow/step/verification state and create pending approval rows."""
    wf_uuid = uuid.UUID(workflow_id)

    result = await db.execute(select(Workflow).where(Workflow.id == wf_uuid))
    workflow = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if workflow is None:
        workflow = Workflow(
            id=wf_uuid,
            user_request=state.get("user_request", ""),
            role=state.get("role", ""),
            created_at=state.get("created_at", now),
        )
        db.add(workflow)

    workflow.user_id = uuid.UUID(user_id) if user_id else None
    workflow.user_request = state.get("user_request", "")
    workflow.role = state.get("role", "")
    workflow.status = state.get("status", "PENDING")
    workflow.plan = state.get("plan", [])
    workflow.final_result = state.get("final_result")
    workflow.updated_at = state.get("updated_at", now)

    existing_steps_result = await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == wf_uuid))
    existing_steps = {s.step_index: s for s in existing_steps_result.scalars().all()}

    for plan_step in state.get("plan", []):
        step_index = plan_step["step_index"]
        step_row = existing_steps.get(step_index)
        if step_row is None:
            step_row = WorkflowStep(workflow_id=wf_uuid, step_index=step_index, tool_name=plan_step["tool_name"])
            db.add(step_row)
            existing_steps[step_index] = step_row

        step_row.tool_name = plan_step["tool_name"]
        step_row.arguments = plan_step.get("arguments", {})
        step_row.result = state.get("results", {}).get(step_index)
        step_row.error = state.get("errors", {}).get(step_index)
        step_row.risk_level = state.get("risk_levels", {}).get(step_index)
        step_row.attempt_count = state.get("attempt_counts", {}).get(step_index, 0)
        step_row.latency_ms = state.get("step_latency_ms", {}).get(step_index)
        step_row.status = _step_status(step_index, state)

        verification = state.get("verifications", {}).get(step_index)
        if verification is not None:
            await db.flush()
            verification_result = await db.execute(
                select(Verification).where(Verification.workflow_step_id == step_row.id)
            )
            verification_row = verification_result.scalar_one_or_none()
            if verification_row is None:
                verification_row = Verification(workflow_step_id=step_row.id, passed=verification["passed"])
                db.add(verification_row)
            verification_row.expected = verification.get("expected")
            verification_row.actual = verification.get("actual")
            verification_row.passed = verification.get("passed", False)
            verification_row.notes = verification.get("notes")

    if state.get("status") == "AWAITING_APPROVAL":
        idx = state.get("current_step_index")
        step_row = existing_steps.get(idx)
        if step_row is not None:
            await db.flush()
            await _ensure_pending_approval(db, step_row)

    await db.commit()


async def record_approval_decision(
    db: AsyncSession,
    workflow_id: str,
    step_index: int,
    decided_by: str | None,
    approve: bool,
    reason: str | None = None,
) -> uuid.UUID:
    """Resolve the pending approval row for a workflow step exactly once."""
    wf_uuid = uuid.UUID(workflow_id)
    result = await db.execute(
        select(WorkflowStep).where(
            WorkflowStep.workflow_id == wf_uuid,
            WorkflowStep.step_index == step_index,
        )
    )
    step_row = result.scalar_one_or_none()
    if step_row is None:
        raise LookupError(f"No persisted workflow step {step_index} for workflow '{workflow_id}'.")

    approval = await _ensure_pending_approval(db, step_row)
    approval.decided_at = datetime.now(timezone.utc)
    approval.decided_by = uuid.UUID(decided_by) if decided_by else None
    approval.decision = "APPROVED" if approve else "REJECTED"
    approval.reason = reason
    await db.commit()
    return approval.id


async def list_workflow_summaries(
    db: AsyncSession, *, user_id: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """Return recent workflow summaries for the dashboard.

    Non-privileged callers pass ``user_id`` so the query is scoped before
    rows leave the database. Managers and admins intentionally pass ``None``
    to review organization-wide approvals.
    """
    statement = (
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .order_by(Workflow.updated_at.desc())
        .limit(limit)
    )
    if user_id is not None:
        statement = statement.where(Workflow.user_id == uuid.UUID(user_id))

    result = await db.execute(statement)
    workflows = result.scalars().unique().all()
    return [
        {
            "id": str(workflow.id),
            "status": workflow.status,
            "user_request": workflow.user_request,
            "role": workflow.role,
            "current_step_index": _current_step_index_from_steps(
                workflow.status,
                [
                    {"step_index": step.step_index, "status": step.status}
                    for step in workflow.steps
                ],
            ),
            "step_count": len(workflow.steps),
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
        }
        for workflow in workflows
    ]


async def load_workflow_state(db: AsyncSession, workflow_id: str) -> dict[str, Any] | None:
    """Read a workflow, steps, verifications and approvals back as a plain dict."""
    wf_uuid = uuid.UUID(workflow_id)
    result = await db.execute(
        select(Workflow)
        .options(
            selectinload(Workflow.steps).selectinload(WorkflowStep.verification),
            selectinload(Workflow.steps).selectinload(WorkflowStep.approvals),
        )
        .where(Workflow.id == wf_uuid)
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        return None

    persisted_plan = workflow.plan or []
    descriptions = {
        int(step["step_index"]): step.get("description", "")
        for step in persisted_plan
        if isinstance(step, dict) and "step_index" in step
    }
    steps = []
    for s in sorted(workflow.steps, key=lambda row: row.step_index):
        approvals = sorted(s.approvals, key=lambda a: a.requested_at)
        latest_approval = approvals[-1] if approvals else None
        steps.append(
            {
                "step_index": s.step_index,
                "tool_name": s.tool_name,
                "arguments": s.arguments,
                "description": descriptions.get(s.step_index, ""),
                "result": s.result,
                "error": s.error,
                "risk_level": s.risk_level,
                "status": s.status,
                "attempt_count": s.attempt_count,
                "latency_ms": s.latency_ms,
                "verification": (
                    None
                    if s.verification is None
                    else {
                        "expected": s.verification.expected,
                        "actual": s.verification.actual,
                        "passed": s.verification.passed,
                        "notes": s.verification.notes,
                    }
                ),
                "approval": (
                    None
                    if latest_approval is None
                    else {
                        "id": str(latest_approval.id),
                        "requested_at": latest_approval.requested_at,
                        "decided_at": latest_approval.decided_at,
                        "decided_by": str(latest_approval.decided_by) if latest_approval.decided_by else None,
                        "decision": latest_approval.decision,
                        "reason": latest_approval.reason,
                    }
                ),
            }
        )

    return {
        "id": str(workflow.id),
        "status": workflow.status,
        "user_request": workflow.user_request,
        "role": workflow.role,
        "plan": persisted_plan,
        "final_result": workflow.final_result,
        "current_step_index": _current_step_index_from_steps(workflow.status, steps),
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
        "steps": steps,
    }


async def load_workflow_execution_state(db: AsyncSession, workflow_id: str) -> WorkflowState | None:
    """Rehydrate enough graph state to resume a persisted paused workflow after restart."""
    record = await load_workflow_state(db, workflow_id)
    if record is None:
        return None
    steps = record.get("steps", [])
    return WorkflowState(
        user_request=record.get("user_request", ""),
        role=record.get("role", "analyst"),
        plan=[
            {
                "step_index": s["step_index"],
                "tool_name": s["tool_name"],
                "arguments": s.get("arguments") or {},
                "description": s.get("description", ""),
            }
            for s in steps
        ],
        current_step_index=record.get("current_step_index", 0),
        results={s["step_index"]: s["result"] for s in steps if s.get("result") is not None},
        errors={s["step_index"]: s["error"] for s in steps if s.get("error") is not None},
        attempt_counts={s["step_index"]: s.get("attempt_count", 0) for s in steps},
        risk_levels={s["step_index"]: s["risk_level"] for s in steps if s.get("risk_level") is not None},
        approved_steps=set(),
        approvals={
            s["step_index"]: s["approval"]
            for s in steps
            if s.get("approval") is not None
        },
        verifications={s["step_index"]: s["verification"] for s in steps if s.get("verification") is not None},
        step_latency_ms={s["step_index"]: s["latency_ms"] for s in steps if s.get("latency_ms") is not None},
        status=record.get("status", "PENDING"),
        final_result=record.get("final_result"),
        last_step_passed=True,
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )
