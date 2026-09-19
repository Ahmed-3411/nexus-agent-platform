"""Database-backed approval recovery tests across a simulated process restart."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from agents import runner  # noqa: E402
from db.models import Approval, Base, Workflow, WorkflowStep  # noqa: E402


def _engine(db_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


async def _initialize(db_path: Path) -> None:
    engine = _engine(db_path)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _read_persisted_state(db_path: Path, workflow_id: str):
    engine = _engine(db_path)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        workflow_uuid = uuid.UUID(workflow_id)
        workflow = await db.scalar(select(Workflow).where(Workflow.id == workflow_uuid))
        step = await db.scalar(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_uuid)
        )
        approval = await db.scalar(
            select(Approval).where(Approval.workflow_step_id == step.id)
        )
    await engine.dispose()
    return workflow, step, approval


@pytest.fixture(autouse=True)
def _clean_process_store():
    runner._workflow_store.clear()
    yield
    runner._workflow_store.clear()


@pytest.mark.asyncio
async def test_approve_survives_restart_and_executes_side_effect_once(tmp_path):
    db_path = tmp_path / "approval-recovery.db"
    await _initialize(db_path)
    plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "x@example.com"}}]

    first_engine = _engine(db_path)
    first_sessions = async_sessionmaker(first_engine, expire_on_commit=False)
    async with first_sessions() as db:
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, paused = await runner.start_workflow("email customer", "manager", db=db)
    await first_engine.dispose()

    workflow, step, approval = await _read_persisted_state(db_path, workflow_id)
    assert paused["status"] == workflow.status == step.status == "AWAITING_APPROVAL"
    assert approval.decision is None

    # Simulate application restart: all in-memory state and DB connections are gone.
    runner._workflow_store.clear()
    second_engine = _engine(db_path)
    second_sessions = async_sessionmaker(second_engine, expire_on_commit=False)
    execute = AsyncMock(return_value={"message_id": "m1", "thread_id": "t1"})
    async with second_sessions() as db:
        with patch("agents.graph.execute_step", new=execute):
            resumed = await runner.approve_step(workflow_id, True, db=db, reason="reviewed")
    await second_engine.dispose()

    assert resumed["status"] == "SUCCEEDED"
    execute.assert_awaited_once()
    workflow, step, approval = await _read_persisted_state(db_path, workflow_id)
    assert workflow.status == step.status == "SUCCEEDED"
    assert approval.decision == "APPROVED"
    assert approval.reason == "reviewed"

    # A replay after another restart cannot execute the external side effect again.
    runner._workflow_store.clear()
    third_engine = _engine(db_path)
    third_sessions = async_sessionmaker(third_engine, expire_on_commit=False)
    async with third_sessions() as db:
        with patch("agents.graph.execute_step", new=execute):
            with pytest.raises(runner.WorkflowNotAwaitingApprovalError):
                await runner.approve_step(workflow_id, True, db=db)
    await third_engine.dispose()
    assert execute.await_count == 1


@pytest.mark.asyncio
async def test_reject_survives_restart_without_executing_side_effect(tmp_path):
    db_path = tmp_path / "rejection-recovery.db"
    await _initialize(db_path)
    plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "x@example.com"}}]

    first_engine = _engine(db_path)
    sessions = async_sessionmaker(first_engine, expire_on_commit=False)
    async with sessions() as db:
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, _ = await runner.start_workflow("email customer", "manager", db=db)
    await first_engine.dispose()

    runner._workflow_store.clear()
    second_engine = _engine(db_path)
    sessions = async_sessionmaker(second_engine, expire_on_commit=False)
    execute = AsyncMock()
    async with sessions() as db:
        with patch("agents.graph.execute_step", new=execute):
            rejected = await runner.approve_step(workflow_id, False, db=db, reason="unsafe")
    await second_engine.dispose()

    assert rejected["status"] == "FAILED"
    execute.assert_not_awaited()
    workflow, step, approval = await _read_persisted_state(db_path, workflow_id)
    assert workflow.status == "FAILED"
    assert step.status == "FAILED"
    assert approval.decision == "REJECTED"
    assert approval.reason == "unsafe"
