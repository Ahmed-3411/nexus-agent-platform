"""
Shared state for the LangGraph workflow engine.

This mirrors the `workflows` / `workflow_steps` tables in
backend/db/schema.sql conceptually, but lives in memory while a graph run
is executing. The runner persists checkpoints to PostgreSQL at API boundaries.
"""
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
WorkflowStatus = Literal[
    "PENDING", "PLANNING", "RUNNING", "AWAITING_APPROVAL", "SUCCEEDED", "FAILED"
]


class PlanStep(TypedDict):
    step_index: int
    tool_name: str
    arguments: dict[str, Any]
    description: str


class WorkflowState(TypedDict, total=False):
    # Input
    user_request: str
    role: str  # the role of the user who triggered this run; drives PolicyEngine checks

    # Planner output
    plan: list[PlanStep]

    # Execution progress
    current_step_index: int
    results: dict[int, Any]
    errors: dict[int, str]
    attempt_counts: dict[int, int]
    risk_levels: dict[int, RiskLevel]
    approved_steps: set[int]
    approvals: dict[int, Any]
    verifications: dict[int, Any]  # step_index -> VerificationRecord (see agents/verifier.py)
    step_latency_ms: dict[int, int]  # step_index -> wall-clock time of its last execution attempt

    # Overall run state
    status: WorkflowStatus
    final_result: Any
    last_step_passed: bool
    created_at: datetime
    updated_at: datetime


def new_workflow_state(user_request: str, role: str = "analyst") -> WorkflowState:
    """
    Build a fresh WorkflowState for a new user request.

    `role` defaults to the least-privileged built-in role ("analyst") so
    that callers who forget to pass the real authenticated user's role
    fail closed (denied by the Policy Engine) rather than fail open.
    """
    now = datetime.now(timezone.utc)
    return WorkflowState(
        user_request=user_request,
        role=role,
        plan=[],
        current_step_index=0,
        results={},
        errors={},
        attempt_counts={},
        risk_levels={},
        approved_steps=set(),
        approvals={},
        verifications={},
        step_latency_ms={},
        status="PENDING",
        final_result=None,
        last_step_passed=True,
        created_at=now,
        updated_at=now,
    )
