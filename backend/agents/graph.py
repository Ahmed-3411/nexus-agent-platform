"""
The core LangGraph workflow: Planner -> risk check -> Executor -> Verifier
-> Recovery, looping over plan steps until the plan succeeds, fails, or
pauses for human approval.

    User Request
         |
      Planner
         |
    risk_check  <---------------------+
         |  (policy denied)           |
         |------------------> END (FAILED)
         |  (approval needed)         |
         |------------------> END (AWAITING_APPROVAL)
         |  (proceed)                 |
      Executor                        |
         |                            |
      Verifier                        |
      |      |                       |
   passed   failed                    |
      |      |                        |
      |   Recovery                    |
      |    |     |                    |
      |  retry  give_up               |
      |    |     |                    |
      |    +-----+--------------------+ (retry -> Executor again)
      |          |
      |          v
      |         END (FAILED)
      |
  more steps? --yes--> risk_check (next step) [loops back up]
      |
      no
      v
   END (SUCCEEDED)

`risk_check_node` uses the real PolicyEngine and RiskEngine, while the
approval endpoints persist and resume `AWAITING_APPROVAL` runs without
replanning.
"""
import time
from copy import deepcopy

from langgraph.graph import END, StateGraph

from agents import mcp_client
from agents.executor import execute_step
from agents.planner import generate_plan
from agents.recovery import classify_error, decide_recovery
from agents.state import WorkflowState
from agents.verifier import verify_result
from policies.engine import PolicyEngine
from risk.engine import RiskEngine

_policy_engine = PolicyEngine()
_risk_engine = RiskEngine()


async def planner_node(state: WorkflowState) -> dict:
    plan = generate_plan(state["user_request"])
    if not plan:
        return {"plan": [], "status": "FAILED", "final_result": {"error": "No plan could be generated."}}
    return {"plan": plan, "current_step_index": 0, "status": "RUNNING"}


def risk_check_node(state: WorkflowState) -> dict:
    """
    Gate the current step on two independent checks, in order:

      1. PolicyEngine: is this role even allowed to use this tool at
         all? If not, the run fails immediately (fail closed) with the
         policy's reason recorded — no partial execution, no silent
         downgrade to a lower-risk path.
      2. RiskEngine: given that it's allowed, does this risk level
         require a human in the loop before proceeding?

    A step already present in `approved_steps` (set by the approval
    endpoint in a resumed run — Phase 5) skips the human-in-the-loop
    pause and proceeds straight to execution.
    """
    idx = state["current_step_index"]
    step = state["plan"][idx]
    role = state.get("role", "analyst")

    decision = _policy_engine.evaluate(role, step["tool_name"])

    risk_levels = dict(state.get("risk_levels", {}))
    risk_levels[idx] = decision["risk_level"]

    if not decision["allowed"]:
        errors = dict(state.get("errors", {}))
        errors[idx] = f"Policy denied: {decision['reason']}"
        return {
            "risk_levels": risk_levels,
            "errors": errors,
            "status": "FAILED",
            "final_result": {"error": f"Step {idx} denied by policy: {decision['reason']}"},
        }

    assessment = _risk_engine.decide(decision["risk_level"])
    if assessment["requires_human"] and idx not in state.get("approved_steps", set()):
        return {"risk_levels": risk_levels, "status": "AWAITING_APPROVAL"}

    return {"risk_levels": risk_levels, "status": "RUNNING"}


async def executor_node(state: WorkflowState) -> dict:
    idx = state["current_step_index"]
    step = state["plan"][idx]

    results = dict(state.get("results", {}))
    errors = dict(state.get("errors", {}))
    step_latency_ms = dict(state.get("step_latency_ms", {}))

    started_at = time.monotonic()
    try:
        result = await execute_step(step)
        results[idx] = result
        if isinstance(result, dict) and result.get("ok") is False:
            errors[idx] = str(result.get("error") or "MCP tool failed without an error message")
        else:
            errors.pop(idx, None)
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any tool failure is recoverable
        errors[idx] = mcp_client.format_exception(exc)
    finally:
        step_latency_ms[idx] = round((time.monotonic() - started_at) * 1000)

    return {"results": results, "errors": errors, "step_latency_ms": step_latency_ms}


def verifier_node(state: WorkflowState) -> dict:
    idx = state["current_step_index"]
    step = state["plan"][idx]
    record = verify_result(
        step["tool_name"], state.get("results", {}).get(idx), state.get("errors", {}).get(idx)
    )

    verifications = dict(state.get("verifications", {}))
    verifications[idx] = record

    if record["passed"]:
        next_index = idx + 1
        if next_index >= len(state["plan"]):
            return {
                "current_step_index": next_index,
                "verifications": verifications,
                "status": "SUCCEEDED",
                "final_result": deepcopy(state.get("results", {})),
                "last_step_passed": True,
            }
        return {
            "current_step_index": next_index,
            "verifications": verifications,
            "status": "RUNNING",
            "last_step_passed": True,
        }

    # Step failed verification (or errored outright): index stays the
    # same; recovery_node decides retry vs. give up. If the tool itself
    # didn't raise an error but the verification rule caught a mismatch
    # (e.g. reported count != actual list length), record that as an
    # error too so recovery_node's error classification sees it.
    errors = dict(state.get("errors", {}))
    errors.setdefault(idx, record["notes"])
    return {"verifications": verifications, "errors": errors, "status": "RUNNING", "last_step_passed": False}


def recovery_node(state: WorkflowState) -> dict:
    idx = state["current_step_index"]
    attempt_counts = dict(state.get("attempt_counts", {}))
    attempt_counts[idx] = attempt_counts.get(idx, 0) + 1

    error = state.get("errors", {}).get(idx)
    decision = decide_recovery(attempt_counts[idx], error)
    if decision == "give_up":
        error_class = classify_error(error)
        step_result = state.get("results", {}).get(idx)
        return {
            "attempt_counts": attempt_counts,
            "status": "FAILED",
            "final_result": {
                "error": f"Step {idx} failed after {attempt_counts[idx]} attempt(s) "
                f"({error_class} error): {error}",
                "step_index": idx,
                "tool_name": state["plan"][idx]["tool_name"],
                **({"tool_result": step_result} if step_result is not None else {}),
            },
        }
    return {"attempt_counts": attempt_counts, "status": "RUNNING"}


def route_after_planner(state: WorkflowState) -> str:
    return "end" if state["status"] == "FAILED" else "risk_check"


def route_after_risk_check(state: WorkflowState) -> str:
    return "end" if state["status"] in ("AWAITING_APPROVAL", "FAILED") else "executor"


def route_after_verifier(state: WorkflowState) -> str:
    idx_before = state["current_step_index"]
    if state["status"] == "SUCCEEDED":
        return "end"
    error_recorded = idx_before < len(state["plan"]) and state["current_step_index"] == idx_before
    # verifier_node leaves current_step_index unchanged on failure and
    # advances it on success, so an unchanged index plus a recorded error
    # for that index means the step failed.
    if error_recorded and state.get("errors", {}).get(idx_before) is not None:
        return "recovery"
    return "risk_check"  # advanced to the next step, or looping is done


def route_after_recovery(state: WorkflowState) -> str:
    return "end" if state["status"] == "FAILED" else "executor"


def build_graph():
    graph = StateGraph(WorkflowState)

    graph.add_node("planner", planner_node)
    graph.add_node("risk_check", risk_check_node)
    graph.add_node("executor", executor_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("recovery", recovery_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges("planner", route_after_planner, {"risk_check": "risk_check", "end": END})
    graph.add_conditional_edges("risk_check", route_after_risk_check, {"executor": "executor", "end": END})
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"recovery": "recovery", "risk_check": "risk_check", "end": END},
    )
    graph.add_conditional_edges("recovery", route_after_recovery, {"executor": "executor", "end": END})

    return graph.compile()


def build_resume_graph():
    """
    Same nodes and edges as build_graph(), minus the Planner — entry
    point is risk_check instead of planner.

    Used by agents/runner.py to resume a run that paused at
    AWAITING_APPROVAL: re-running the Planner on resume would generate a
    brand new plan from the original user request (wasting an LLM call
    and potentially producing a different plan than the one a human just
    approved a step of), so resuming re-enters the graph at the step that
    was paused instead.
    """
    graph = StateGraph(WorkflowState)

    graph.add_node("risk_check", risk_check_node)
    graph.add_node("executor", executor_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("recovery", recovery_node)

    graph.set_entry_point("risk_check")

    graph.add_conditional_edges("risk_check", route_after_risk_check, {"executor": "executor", "end": END})
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"recovery": "recovery", "risk_check": "risk_check", "end": END},
    )
    graph.add_conditional_edges("recovery", route_after_recovery, {"executor": "executor", "end": END})

    return graph.compile()
