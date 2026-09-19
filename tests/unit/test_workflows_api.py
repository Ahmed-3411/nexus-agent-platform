"""
Tests for the /workflows API endpoints.

These test the FastAPI layer only — request/response shapes, status
codes, error mapping, and the auth/role checks added when the client-
supplied `role` field was removed — by mocking agents.runner entirely,
so they don't need langgraph, a real LLM, or MCP servers.

Authentication is exercised via FastAPI's dependency_overrides rather
than real JWTs: each test overrides get_current_user with whichever
CurrentUser (and role) it wants to simulate, then restores the default
(no override, so the real dependency runs and requires a real header)
afterwards. The "no token at all" tests deliberately do NOT override
get_current_user, so the real dependency's 401 is what's exercised.

Requires: pip install -r backend/requirements.txt pytest pytest-asyncio
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.runner import WorkflowNotAwaitingApprovalError, WorkflowNotFoundError  # noqa: E402
from agents.state import new_workflow_state  # noqa: E402
from auth.dependencies import CurrentUser, get_current_user  # noqa: E402
from db.session import get_db  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)


def _as_user(role: str, user_id: str = "user-1", email: str = "a@b.com"):
    """Override get_current_user for the duration of a `with` block."""

    def _override():
        return CurrentUser(id=user_id, email=email, role=role)

    return _override


def _succeeded_state(user_request="do the thing", role="analyst"):
    state = new_workflow_state(user_request, role=role)
    state["status"] = "SUCCEEDED"
    state["plan"] = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
    state["results"] = {0: {"count": 0, "files": []}}
    state["final_result"] = {0: {"count": 0, "files": []}}
    return state


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Every test starts with a clean dependency_overrides dict, but keeps
    get_db overridden throughout (no test here actually touches the DB,
    since agents.runner.start_workflow/approve_step are mocked outright)."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


class TestCreateWorkflow:
    def test_returns_serialized_state_using_authenticated_users_role(self):
        fake_state = _succeeded_state(role="manager")
        app.dependency_overrides[get_current_user] = _as_user("manager")

        with patch(
            "api.workflows.start_workflow", new=AsyncMock(return_value=("wf-1", fake_state))
        ) as mock_start:
            response = client.post("/workflows", json={"request": "do the thing"})

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "wf-1"
        assert body["role"] == "manager"
        assert body["created_at"] is not None
        assert body["updated_at"] is not None
        assert mock_start.call_args.args[:2] == ("do the thing", "manager")
        assert mock_start.call_args.kwargs["user_id"] == "user-1"

    def test_request_body_no_longer_accepts_a_role_field(self):
        # A client sending role="admin" in the body must have no effect —
        # the role that matters comes only from the auth dependency.
        fake_state = _succeeded_state(role="analyst")
        app.dependency_overrides[get_current_user] = _as_user("analyst")

        with patch(
            "api.workflows.start_workflow", new=AsyncMock(return_value=("wf-2", fake_state))
        ) as mock_start:
            client.post("/workflows", json={"request": "do the thing", "role": "admin"})

        assert mock_start.call_args.args[:2] == ("do the thing", "analyst")

    def test_missing_auth_token_returns_401(self):
        # No dependency_overrides here: the real get_current_user runs.
        response = client.post("/workflows", json={"request": "do the thing"})
        assert response.status_code == 401


class TestListWorkflows:
    def test_analyst_list_is_scoped_to_authenticated_user(self):
        app.dependency_overrides[get_current_user] = _as_user(
            "analyst", user_id="f9d99e3b-21fb-444b-a076-f496de89c28c"
        )
        now = datetime.now(timezone.utc)
        records = [{
            "id": "c83c2e14-d9d0-4b21-bfe4-c93fdad208b4",
            "status": "RUNNING",
            "user_request": "find reports",
            "role": "analyst",
            "current_step_index": 0,
            "step_count": 2,
            "created_at": now,
            "updated_at": now,
        }]
        with patch(
            "db.workflow_repository.list_workflow_summaries",
            new=AsyncMock(return_value=records),
        ) as mock_list:
            response = client.get("/workflows")

        assert response.status_code == 200
        assert response.json()[0]["status"] == "RUNNING"
        assert mock_list.call_args.kwargs["user_id"] == "f9d99e3b-21fb-444b-a076-f496de89c28c"

    def test_manager_list_is_not_user_scoped(self):
        app.dependency_overrides[get_current_user] = _as_user("manager")
        with patch(
            "db.workflow_repository.list_workflow_summaries",
            new=AsyncMock(return_value=[]),
        ) as mock_list:
            response = client.get("/workflows")

        assert response.status_code == 200
        assert mock_list.call_args.kwargs["user_id"] is None


class TestGetWorkflow:
    def test_returns_404_for_unknown_id(self):
        app.dependency_overrides[get_current_user] = _as_user("analyst")
        with (
            patch("api.workflows.get_workflow", return_value=None),
            patch("db.workflow_repository.load_workflow_state", new=AsyncMock(return_value=None)),
        ):
            response = client.get("/workflows/not-a-real-id")
        assert response.status_code == 404

    def test_returns_serialized_state_for_known_id(self):
        app.dependency_overrides[get_current_user] = _as_user("analyst")
        fake_state = _succeeded_state()
        with patch("api.workflows.get_workflow", return_value=fake_state):
            response = client.get("/workflows/wf-1")
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCEEDED"

    def test_falls_back_to_db_when_not_in_memory(self):
        # Simulates reading a workflow created by a different (or since-
        # restarted) API process: nothing in agents.runner's in-memory
        # store, but a row exists in Postgres.
        app.dependency_overrides[get_current_user] = _as_user("analyst")
        db_record = {
            "id": "wf-9",
            "status": "SUCCEEDED",
            "user_request": "find the report",
            "role": "analyst",
            "final_result": {"0": {"count": 1}},
            "steps": [
                {
                    "step_index": 0,
                    "tool_name": "drive.search",
                    "arguments": {"query": "report"},
                    "result": {"count": 1, "files": [{"id": "f1"}]},
                    "error": None,
                    "risk_level": "LOW",
                    "status": "SUCCEEDED",
                    "attempt_count": 0,
                    "latency_ms": 12,
                    "verification": {"expected": 1, "actual": 1, "passed": True, "notes": "ok"},
                }
            ],
        }
        with (
            patch("api.workflows.get_workflow", return_value=None),
            patch("db.workflow_repository.load_workflow_state", new=AsyncMock(return_value=db_record)),
        ):
            response = client.get("/workflows/wf-9")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "SUCCEEDED"
        assert body["plan"][0]["tool_name"] == "drive.search"
        assert body["results"]["0"] == {"count": 1, "files": [{"id": "f1"}]}
        assert body["verifications"]["0"]["passed"] is True

    def test_missing_auth_token_returns_401(self):
        response = client.get("/workflows/wf-1")
        assert response.status_code == 401


class TestApproveAndReject:
    def test_manager_can_approve(self):
        fake_state = _succeeded_state()
        app.dependency_overrides[get_current_user] = _as_user("manager")
        with patch("api.workflows.approve_step", new=AsyncMock(return_value=fake_state)) as mock_approve:
            response = client.post("/workflows/wf-1/approve")
        assert response.status_code == 200
        assert mock_approve.call_args.args[:2] == ("wf-1", True)

    def test_admin_can_reject(self):
        fake_state = _succeeded_state()
        fake_state["status"] = "FAILED"
        fake_state["final_result"] = {"error": "Step 0 was rejected by a human reviewer."}
        app.dependency_overrides[get_current_user] = _as_user("admin")
        with patch("api.workflows.approve_step", new=AsyncMock(return_value=fake_state)) as mock_approve:
            response = client.post("/workflows/wf-1/reject")
        assert response.status_code == 200
        assert response.json()["status"] == "FAILED"
        assert mock_approve.call_args.args[:2] == ("wf-1", False)

    def test_analyst_cannot_approve(self):
        app.dependency_overrides[get_current_user] = _as_user("analyst")
        with patch("api.workflows.approve_step", new=AsyncMock()) as mock_approve:
            response = client.post("/workflows/wf-1/approve")
        assert response.status_code == 403
        mock_approve.assert_not_called()

    def test_support_agent_cannot_reject(self):
        app.dependency_overrides[get_current_user] = _as_user("support_agent")
        with patch("api.workflows.approve_step", new=AsyncMock()) as mock_approve:
            response = client.post("/workflows/wf-1/reject")
        assert response.status_code == 403
        mock_approve.assert_not_called()

    def test_approve_unknown_workflow_returns_404(self):
        app.dependency_overrides[get_current_user] = _as_user("admin")
        with patch(
            "api.workflows.approve_step",
            new=AsyncMock(side_effect=WorkflowNotFoundError("no such workflow")),
        ):
            response = client.post("/workflows/ghost/approve")
        assert response.status_code == 404

    def test_approve_non_paused_workflow_returns_409(self):
        app.dependency_overrides[get_current_user] = _as_user("admin")
        with patch(
            "api.workflows.approve_step",
            new=AsyncMock(side_effect=WorkflowNotAwaitingApprovalError("not paused")),
        ):
            response = client.post("/workflows/wf-1/approve")
        assert response.status_code == 409

    def test_missing_auth_token_returns_401_before_role_check(self):
        response = client.post("/workflows/wf-1/approve")
        assert response.status_code == 401
