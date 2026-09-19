"""
Workflow endpoints.

Phase 0 shipped stubs so the frontend contract could stabilize before the
LangGraph engine existed. Phase 5 replaced those stubs with real calls
into agents/runner.py. Closing the auth gap removes the client-supplied
`role` field entirely: every endpoint now requires a valid bearer token
(see auth/dependencies.py), and workflows run as the authenticated
user's real role from that token — a caller can no longer just claim to
be an admin. Approving/rejecting a step additionally requires the
"admin" or "manager" role, since that's itself a privileged action.

Every write endpoint now also persists to Postgres (db/workflow_repository.py)
via agents/runner.py's optional `db`/`user_id` parameters — a workflow
survives an API process restart, not just repeated requests within one
process. GET /workflows/{id} reads the fast in-memory path first and
only falls back to the database if that returns nothing (i.e. a
different/restarted process created the workflow).

    POST /workflows                -> start_workflow()
    GET  /workflows/{id}           -> get_workflow(), falling back to
                                       db/workflow_repository.load_workflow_state()
    POST /workflows/{id}/approve   -> approve_step(approve=True)
    POST /workflows/{id}/reject    -> approve_step(approve=False)
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agents.runner import (
    WorkflowNotAwaitingApprovalError,
    WorkflowNotFoundError,
    approve_step,
    get_workflow,
    start_workflow,
)
from agents.state import WorkflowState
from auth.dependencies import CurrentUser, get_current_user
from db.session import get_db

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowCreateRequest(BaseModel):
    request: str


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = None


class WorkflowResponse(BaseModel):
    id: str
    status: str
    user_request: str
    role: str
    current_step_index: int
    plan: list[dict[str, Any]]
    results: dict[str, Any]
    errors: dict[str, Any]
    risk_levels: dict[str, Any]
    verifications: dict[str, Any]
    approved_steps: list[int]
    approvals: dict[str, Any] = Field(default_factory=dict)
    final_result: Any = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkflowSummaryResponse(BaseModel):
    id: str
    status: str
    user_request: str
    role: str
    current_step_index: int
    step_count: int
    created_at: datetime
    updated_at: datetime


def _serialize(workflow_id: str, state: WorkflowState) -> WorkflowResponse:
    # WorkflowState uses int keys for per-step dicts and a set for
    # approved_steps; JSON has neither, so normalize both here.
    approved_steps = sorted(state.get("approved_steps", set()))
    approvals: dict[str, Any] = {
        str(step): record for step, record in state.get("approvals", {}).items()
    }
    approvals.update({
        str(step): {"decision": "APPROVED"} for step in approved_steps
        if str(step) not in approvals
    })
    if state.get("status") == "AWAITING_APPROVAL":
        approvals[str(state.get("current_step_index", 0))] = {"decision": None}

    return WorkflowResponse(
        id=workflow_id,
        status=state.get("status", "PENDING"),
        user_request=state.get("user_request", ""),
        role=state.get("role", ""),
        current_step_index=state.get("current_step_index", 0),
        plan=state.get("plan", []),
        results={str(k): v for k, v in state.get("results", {}).items()},
        errors={str(k): v for k, v in state.get("errors", {}).items()},
        risk_levels={str(k): v for k, v in state.get("risk_levels", {}).items()},
        verifications={str(k): v for k, v in state.get("verifications", {}).items()},
        approved_steps=approved_steps,
        approvals=approvals,
        final_result=state.get("final_result"),
        created_at=state.get("created_at"),
        updated_at=state.get("updated_at"),
    )


def _serialize_from_db_record(record: dict[str, Any]) -> WorkflowResponse:
    # Shape returned by db.workflow_repository.load_workflow_state() —
    # a flat list of step dicts rather than WorkflowState's per-field
    # dicts keyed by step index. Adapt it to the same WorkflowResponse
    # the in-memory path returns, so API clients see one consistent shape
    # regardless of which path served the read.
    steps = record.get("steps", [])
    return WorkflowResponse(
        id=record["id"],
        status=record.get("status", "PENDING"),
        user_request=record.get("user_request", ""),
        role=record.get("role", ""),
        current_step_index=record.get("current_step_index", max((s["step_index"] for s in steps), default=-1) + 1),
        plan=(record.get("plan") or [
            {
                "step_index": s["step_index"],
                "tool_name": s["tool_name"],
                "arguments": s["arguments"] or {},
                "description": s.get("description", ""),
            }
            for s in steps
        ]),
        results={str(s["step_index"]): s["result"] for s in steps if s["result"] is not None},
        errors={str(s["step_index"]): s["error"] for s in steps if s["error"] is not None},
        risk_levels={str(s["step_index"]): s["risk_level"] for s in steps if s["risk_level"] is not None},
        verifications={str(s["step_index"]): s["verification"] for s in steps if s["verification"] is not None},
        approved_steps=[
            s["step_index"]
            for s in steps
            if (s.get("approval") or {}).get("decision") == "APPROVED"
        ],
        approvals={
            str(s["step_index"]): s["approval"]
            for s in steps
            if s.get("approval") is not None
        },
        final_result=record.get("final_result"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


@router.get("", response_model=list[WorkflowSummaryResponse])
async def list_workflows(
    limit: int = Query(default=100, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowSummaryResponse]:
    """List recent workflows visible to the authenticated user."""
    from db.workflow_repository import list_workflow_summaries

    user_scope = None if current_user.role in ("admin", "manager") else current_user.id
    records = await list_workflow_summaries(db, user_id=user_scope, limit=limit)
    return [WorkflowSummaryResponse(**record) for record in records]


@router.post("", response_model=WorkflowResponse)
async def create_workflow(
    payload: WorkflowCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    workflow_id, state = await start_workflow(
        payload.request, current_user.role, user_id=current_user.id, db=db
    )
    return _serialize(workflow_id, state)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_endpoint(
    workflow_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    state = get_workflow(workflow_id)
    if state is not None:
        return _serialize(workflow_id, state)

    from db.workflow_repository import load_workflow_state

    record = await load_workflow_state(db, workflow_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No workflow found with id '{workflow_id}'.")
    return _serialize_from_db_record(record)


async def _resolve_approval(
    workflow_id: str,
    approve: bool,
    current_user: CurrentUser,
    db: AsyncSession,
    reason: str | None = None,
) -> WorkflowResponse:
    # Approving/rejecting a HIGH/CRITICAL-risk step is itself a
    # privileged action — an analyst shouldn't be able to approve the
    # very email send that the Policy Engine denied them the ability to
    # trigger directly.
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role}' is not permitted to approve or reject workflow steps.",
        )
    try:
        state = await approve_step(
            workflow_id, approve, user_id=current_user.id, db=db, reason=reason
        )
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkflowNotAwaitingApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize(workflow_id, state)


@router.post("/{workflow_id}/approve", response_model=WorkflowResponse)
async def approve_workflow_step(
    workflow_id: str,
    payload: ApprovalDecisionRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    return await _resolve_approval(
        workflow_id, approve=True, current_user=current_user, db=db,
        reason=payload.reason if payload else None,
    )


@router.post("/{workflow_id}/reject", response_model=WorkflowResponse)
async def reject_workflow_step(
    workflow_id: str,
    payload: ApprovalDecisionRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    return await _resolve_approval(
        workflow_id, approve=False, current_user=current_user, db=db,
        reason=payload.reason if payload else None,
    )
