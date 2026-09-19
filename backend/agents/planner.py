"""LLM-backed workflow planner with a safe deterministic fallback.

Provider failures are expected runtime conditions. The planner tries
Anthropic, then OpenAI, and finally produces a conservative read-only plan.
Every provider response is normalized and validated against TOOL_CATALOG.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from anthropic import APIError as AnthropicAPIError
from anthropic import Anthropic
from anthropic import RateLimitError as AnthropicRateLimitError
from openai import APIError as OpenAIAPIError
from openai import OpenAI
from openai import RateLimitError as OpenAIRateLimitError

from agents.sql_safety import extract_explicit_read_only_sql, normalize_read_only_sql
from agents.tool_catalog import TOOL_CATALOG, catalog_prompt_listing

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")


class PlanValidationError(ValueError):
    """Raised when provider output cannot become a safe executable plan."""


def _planner_prompt(user_request: str) -> str:
    return f"""
You are the planning component of an enterprise agent workflow platform.

Convert the user's request into a JSON array of executable workflow steps.
Return ONLY valid JSON, with no markdown fences or explanations.

Each step must have exactly these fields:
[
  {{
    "step_index": 0,
    "tool_name": "tool.name",
    "arguments": {{}},
    "description": "short description of what this step does"
  }}
]

Available logical tools:
{catalog_prompt_listing()}

Rules:
- step_index starts at 0 and increments by one.
- tool_name must be one of the listed logical tools.
- database.query takes {{"sql": "SELECT ..."}} and only accepts a single,
  explicit, read-only SELECT or WITH query. Never put natural language in sql.
- Prefer database.list_tables, database.get_schema, or
  database.describe_table for database discovery.
- Never invent a tool.

User request:
{user_request}
""".strip()


def _extract_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _normalize_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(arguments)

    if tool_name == "database.query":
        candidate = normalized.get("sql", normalized.get("query"))
        if not isinstance(candidate, str):
            raise PlanValidationError("database.query requires a string 'sql' argument")
        try:
            sql = normalize_read_only_sql(candidate)
        except ValueError as exc:
            raise PlanValidationError(str(exc)) from exc
        return {"sql": sql}

    if tool_name == "database.describe_table":
        table_name = normalized.get("table_name", normalized.get("table"))
        if not isinstance(table_name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
            raise PlanValidationError(
                "database.describe_table requires a simple 'table_name' identifier"
            )
        return {"table_name": table_name}

    return normalized


def _normalize_plan_data(data: Any, *, accept_wrappers: bool) -> list[dict[str, Any]]:
    if accept_wrappers and isinstance(data, dict):
        if "plan" in data:
            data = data["plan"]
        elif "steps" in data:
            data = data["steps"]

    if not isinstance(data, list):
        raise PlanValidationError("Planner output must be a JSON array")

    normalized: list[dict[str, Any]] = []
    for index, step in enumerate(data):
        if not isinstance(step, dict):
            raise PlanValidationError(f"Planner step {index} must be an object")

        tool_name = step.get("tool_name", step.get("tool"))
        if not isinstance(tool_name, str) or not tool_name:
            raise PlanValidationError(f"Planner step {index} is missing a valid tool_name")
        if tool_name not in TOOL_CATALOG:
            raise PlanValidationError(f"Planner step {index} uses unsupported tool '{tool_name}'")

        arguments = step.get("arguments", {})
        if not isinstance(arguments, dict):
            raise PlanValidationError(f"Planner step {index} has invalid arguments")

        description = step.get("description") or f"Execute {tool_name}."
        if not isinstance(description, str):
            description = str(description)

        normalized.append(
            {
                "step_index": index,
                "tool_name": tool_name,
                "arguments": _normalize_arguments(tool_name, arguments),
                "description": description,
            }
        )
    return normalized


def _decode_plan(text: str, *, accept_wrappers: bool) -> list[dict[str, Any]]:
    cleaned = _extract_json(text)
    try:
        data = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PlanValidationError("Planner returned invalid JSON") from exc
    return _normalize_plan_data(data, accept_wrappers=accept_wrappers)


def parse_plan_response(text: str) -> list[dict[str, Any]]:
    """Strict public parser retained for callers and unit tests."""
    return _decode_plan(text, accept_wrappers=False)


def _parse_plan(text: str) -> list[dict[str, Any]]:
    """Provider parser that also accepts common ``plan``/``steps`` wrappers."""
    return _decode_plan(text, accept_wrappers=True)


def _step(tool_name: str, arguments: dict[str, Any], description: str) -> list[dict[str, Any]]:
    if tool_name not in TOOL_CATALOG:  # defense in depth for future edits
        raise RuntimeError(f"Fallback references unsupported tool '{tool_name}'")
    return [{
        "step_index": 0,
        "tool_name": tool_name,
        "arguments": _normalize_arguments(tool_name, arguments),
        "description": description,
    }]


def _fallback_plan(user_request: str) -> list[dict[str, Any]]:
    """Create one conservative, deterministic, read-only step."""
    text = user_request.strip()
    lowered = text.lower()

    if "drive" in lowered:
        return _step("drive.search", {"query": text}, "Search Google Drive for relevant content.")

    if any(word in lowered for word in ("email", "gmail", "mail")):
        return _step("gmail.search", {"query": text}, "Search Gmail for relevant messages.")

    describe_match = re.search(
        r"(?:describe|inspect|columns?(?:\s+in|\s+of)?)\s+(?:the\s+)?(?:table\s+)?([A-Za-z_][A-Za-z0-9_]*)",
        text,
        flags=re.IGNORECASE,
    )
    if describe_match and any(word in lowered for word in ("table", "column", "database", "postgres")):
        table_name = describe_match.group(1)
        return _step(
            "database.describe_table",
            {"table_name": table_name},
            f"Describe the {table_name} table.",
        )

    if "schema" in lowered:
        return _step("database.get_schema", {}, "Retrieve the public database schema.")

    if "table" in lowered and any(word in lowered for word in ("list", "show", "available", "database")):
        return _step("database.list_tables", {}, "List available public database tables.")

    explicit_sql = extract_explicit_read_only_sql(text)
    if explicit_sql is not None:
        return _step(
            "database.query",
            {"sql": explicit_sql},
            "Run the explicit read-only SQL query.",
        )

    # Database-like natural language is intentionally not converted to SQL.
    return _step(
        "database.list_tables",
        {},
        "List available tables as a safe read-only fallback.",
    )


def _try_anthropic(user_request: str) -> list[dict[str, Any]] | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": _planner_prompt(user_request)}],
        )
        content = getattr(response, "content", None) or []
        text = getattr(content[0], "text", None) if content else None
        if not isinstance(text, str):
            raise PlanValidationError("Anthropic returned no text plan")
        plan = _parse_plan(text)
        if not plan:
            raise PlanValidationError("Anthropic returned an empty plan")
        return plan
    except (AnthropicRateLimitError, AnthropicAPIError, PlanValidationError) as exc:
        logger.warning("Anthropic planner unavailable; trying OpenAI. reason=%s", type(exc).__name__)
    except Exception as exc:  # provider SDK/network failures are fallback conditions
        logger.warning("Anthropic planner failed; trying OpenAI. reason=%s", type(exc).__name__)
    return None


def _try_openai(user_request: str) -> list[dict[str, Any]] | None:
    if not OPENAI_API_KEY:
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(model=OPENAI_MODEL, input=_planner_prompt(user_request))
        text = getattr(response, "output_text", None)
        if not isinstance(text, str):
            raise PlanValidationError("OpenAI returned no text plan")
        plan = _parse_plan(text)
        if not plan:
            raise PlanValidationError("OpenAI returned an empty plan")
        return plan
    except (OpenAIRateLimitError, OpenAIAPIError, PlanValidationError) as exc:
        logger.warning("OpenAI planner unavailable; using fallback. reason=%s", type(exc).__name__)
    except Exception as exc:  # provider SDK/network failures are fallback conditions
        logger.warning("OpenAI planner failed; using fallback. reason=%s", type(exc).__name__)
    return None


def generate_plan(user_request: str, client: Any | None = None) -> list[dict[str, Any]]:
    """Generate a validated plan without surfacing expected provider failures.

    ``client`` is a backwards-compatible injection seam for isolated tests. In
    normal runtime calls provider selection is Anthropic -> OpenAI -> fallback.
    """
    if client is not None:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": _planner_prompt(user_request)}],
        )
        content = getattr(response, "content", None) or []
        text = getattr(content[0], "text", None) if content else None
        if not isinstance(text, str):
            raise PlanValidationError("Injected planner returned no text plan")
        return parse_plan_response(text)

    plan = _try_anthropic(user_request)
    if plan is not None:
        logger.info("Planner provider: Anthropic")
        return plan

    plan = _try_openai(user_request)
    if plan is not None:
        logger.info("Planner provider: OpenAI")
        return plan

    logger.warning("No LLM planner available; using deterministic read-only fallback")
    return _fallback_plan(user_request)
