"""
Verifier: decides whether a step's execution result counts as a pass,
using tool-specific expected-vs-actual checks where one is meaningful,
and falling back to a basic sanity check otherwise.

This is the concrete version of the "Verification Engine" from the
original project brief: for example, a search tool's own reported count
must match the length of the list it actually returned — if the MCP
server's `count` field and its `files`/`message_ids` list ever disagree,
that is a real bug worth failing the step over, not something to paper
over with the Phase 2 "did we get a truthy result back?" check.

The dict returned by `verify_result` mirrors the `verifications` table
in db/schema.sql (`expected`, `actual`, `passed`, `notes`) so persisting
a verification record once the API layer is wired to the database
(Phase 5+) is a straight field-for-field mapping.
"""
from typing import Any, Callable, TypedDict


class VerificationRecord(TypedDict):
    passed: bool
    expected: Any
    actual: Any
    notes: str


def _verify_count_matches_list(result: dict, count_key: str, list_key: str) -> VerificationRecord:
    expected = result.get(count_key)
    actual_list = result.get(list_key)
    actual = len(actual_list) if isinstance(actual_list, list) else None
    passed = actual is not None and expected == actual
    notes = (
        f"'{count_key}' ({expected}) matches len('{list_key}') ({actual})."
        if passed
        else f"'{count_key}' ({expected}) does NOT match len('{list_key}') ({actual})."
    )
    return VerificationRecord(passed=passed, expected=expected, actual=actual, notes=notes)


def _verify_required_keys_present(result: dict, required_keys: tuple[str, ...]) -> VerificationRecord:
    missing = [k for k in required_keys if not result.get(k)]
    passed = not missing
    notes = "All required fields present." if passed else f"Missing/empty required fields: {missing}."
    return VerificationRecord(
        passed=passed, expected=list(required_keys), actual=list(result.keys()), notes=notes
    )


# Tool-specific verification rules. Each takes the raw tool result dict
# and returns a VerificationRecord. Tools not listed here fall back to
# the basic check in verify_result().
_VERIFICATION_RULES: dict[str, Callable[[dict], VerificationRecord]] = {
    "database.query": lambda r: _verify_count_matches_list(r, "row_count", "rows"),
    "gmail.search": lambda r: _verify_count_matches_list(r, "count", "message_ids"),
    "drive.search": lambda r: _verify_count_matches_list(r, "count", "files"),
    "drive.list": lambda r: _verify_count_matches_list(r, "count", "files"),
    "gmail.send": lambda r: _verify_required_keys_present(r, ("message_id", "thread_id")),
    "gmail.draft": lambda r: _verify_required_keys_present(r, ("draft_id", "message_id")),
}


def verify_result(tool_name: str, result: Any, error: str | None) -> VerificationRecord:
    """
    Verify a single step's execution result.

    If the step errored, that's an automatic fail — no tool-specific rule
    is consulted. Otherwise, a tool-specific rule runs if one exists;
    tools without a specific rule pass as long as they returned a non-null
    result (the Phase 2 behavior, kept as a sane default).
    """
    if error is not None:
        actual = result if isinstance(result, dict) and result.get("ok") is False else error
        return VerificationRecord(
            passed=False, expected="no error", actual=actual, notes=f"Step failed: {error}"
        )

    if result is None:
        return VerificationRecord(
            passed=False, expected="a non-null result", actual=None, notes="Tool returned no result."
        )

    if isinstance(result, dict) and result.get("ok") is False:
        message = str(result.get("error") or "Tool reported failure")
        return VerificationRecord(
            passed=False,
            expected="a successful MCP result",
            actual=result,
            notes=f"Tool reported failure: {message}",
        )

    rule = _VERIFICATION_RULES.get(tool_name)
    if rule is None:
        return VerificationRecord(
            passed=True,
            expected="a non-null result (no tool-specific rule defined)",
            actual=result,
            notes=f"No tool-specific verification rule for '{tool_name}'; basic presence check passed.",
        )

    if not isinstance(result, dict):
        return VerificationRecord(
            passed=False,
            expected="a dict result",
            actual=type(result).__name__,
            notes=f"Tool '{tool_name}' returned a non-dict result, cannot apply its verification rule.",
        )

    return rule(result)
