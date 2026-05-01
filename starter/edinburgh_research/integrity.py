"""Ex5 — reference solution for integrity.py.

verify_dataflow's job: for every concrete fact in the flyer, confirm
that some tool call in the session actually produced that value. If
a fact exists in the flyer but not in any tool output, it's fabrication.

Two competing failure modes to balance:
  - Too lenient → misses fabrications (grader plants £9999; must catch it)
  - Too strict → rejects legitimate flyers (fails the "accepts real flyer" test)

This implementation leans slightly strict but uses the scalar-matching
`fact_appears_in_log` helper provided in the starter to tolerate common
variations (leading £, trailing C, case differences).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict
    output: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


_TOOL_CALL_LOG: list[ToolCallRecord] = []


def record_tool_call(tool_name: str, arguments: dict, output: dict) -> None:
    _TOOL_CALL_LOG.append(
        ToolCallRecord(tool_name=tool_name, arguments=dict(arguments), output=dict(output))
    )


def clear_log() -> None:
    _TOOL_CALL_LOG.clear()


@dataclass
class IntegrityResult:
    ok: bool
    unverified_facts: list[str] = field(default_factory=list)
    verified_facts: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "unverified_facts": self.unverified_facts,
            "verified_facts": self.verified_facts,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def extract_money_facts(text: str) -> list[str]:
    """Find all £<number> occurrences, HTML tags stripped or not."""
    stripped = re.sub(r"<[^>]+>", " ", text)
    return re.findall(r"£\d+(?:\.\d+)?", stripped)


def extract_temperature_facts(text: str) -> list[str]:
    """Find temperature mentions (number followed by °C or C)."""
    stripped = re.sub(r"<[^>]+>", " ", text)
    return list({m.group(1) for m in re.finditer(r"(\d+)\s*°?\s*[Cc]\b", stripped)})


def extract_condition_facts(text: str) -> list[str]:
    """Find weather condition keywords."""
    stripped = re.sub(r"<[^>]+>", " ", text)
    tl = stripped.lower()
    known = ("sunny", "rainy", "cloudy", "partly_cloudy", "partly cloudy")
    return [c for c in known if c in tl]


def extract_testid_facts(text: str) -> dict[str, str]:
    """For HTML flyers that use data-testid, extract {testid: value} pairs."""
    pattern = re.compile(
        r'<[^>]+data-testid="([^"]+)"[^>]*>([^<]+)</[^>]+>',
        re.IGNORECASE,
    )
    return {m.group(1): m.group(2).strip() for m in pattern.finditer(text)}


def _normalise_numeric(val: Any) -> float | None:
    """Try to parse a value as a float after stripping currency/unit symbols."""
    try:
        return float(str(val).lower().strip("£°c% \t"))
    except (ValueError, TypeError):
        return None


def _flatten_values(obj: Any) -> list[Any]:
    """Recursively collect all leaf values from a nested dict/list."""
    if isinstance(obj, dict):
        result = []
        for v in obj.values():
            result.extend(_flatten_values(v))
        return result
    if isinstance(obj, (list, tuple, set)):
        result = []
        for v in obj:
            result.extend(_flatten_values(v))
        return result
    return [obj]


def fact_appears_in_log(fact: Any, log: list[ToolCallRecord] | None = None) -> bool:
    records = log if log is not None else _TOOL_CALL_LOG
    target = str(fact).lower().strip("£°c ")

    def _scan(obj: Any) -> bool:
        if isinstance(obj, (str, int, float)):
            return str(obj).lower().strip("£°c ") == target
        if isinstance(obj, dict):
            return any(_scan(v) for v in obj.values())
        if isinstance(obj, (list, tuple, set)):
            return any(_scan(v) for v in obj)
        return False

    return any(_scan(r.output) or _scan(r.arguments) for r in records)


def _numeric_fact_appears_in_log(
    fact: Any,
    log: list[ToolCallRecord] | None = None,
    tolerance: float = 0.01,
) -> bool:
    """Check numeric facts with float comparison to handle '325.00' vs 325 etc."""
    target = _normalise_numeric(fact)
    if target is None:
        return fact_appears_in_log(fact, log)

    records = log if log is not None else _TOOL_CALL_LOG
    for rec in records:
        for v in _flatten_values(rec.output) + _flatten_values(rec.arguments):
            n = _normalise_numeric(v)
            if n is not None and abs(n - target) <= tolerance:
                return True
    return False


def _get_tool_output(tool_name: str, log: list[ToolCallRecord] | None = None) -> dict | None:
    """Return the output dict of the most recent call to tool_name, or None."""
    records = log if log is not None else _TOOL_CALL_LOG
    for rec in reversed(records):
        if rec.tool_name == tool_name:
            return rec.output
    return None


def _check_required_tools_ran(log: list[ToolCallRecord] | None = None) -> list[str]:
    """Return list of required tools that never appeared in the log."""
    records = log if log is not None else _TOOL_CALL_LOG
    ran = {r.tool_name for r in records}
    required = {"venue_search", "get_weather", "calculate_cost"}
    return sorted(required - ran)


# ---------------------------------------------------------------------------
# verify_dataflow — the main check
# ---------------------------------------------------------------------------
def verify_dataflow(flyer_content: str) -> IntegrityResult:
    if not flyer_content or not flyer_content.strip():
        return IntegrityResult(ok=True, summary="no facts to verify (empty flyer)")

    # ------------------------------------------------------------------
    # Gate 1: required tools must have run (accumulated, don't return early)
    # ------------------------------------------------------------------
    missing_tools = _check_required_tools_ran()
    unverified: list[str] = [f"tool_never_ran:{t}" for t in missing_tools]
    verified: list[str] = []

    # ------------------------------------------------------------------
    # Gate 2: per-tool output verification
    # ------------------------------------------------------------------
    venue_output = _get_tool_output("venue_search")
    weather_output = _get_tool_output("get_weather")
    cost_output = _get_tool_output("calculate_cost")

    def _fail(label: str, value: Any) -> None:
        unverified.append(f"{label}={value}")

    def _pass(label: str, value: Any) -> None:
        verified.append(f"{label}={value}")

    # --- Venue facts (must come from venue_search output) ---
    testid = extract_testid_facts(flyer_content)

    for field_name in ("venue_name", "venue-name", "name"):
        if field_name in testid:
            v = testid[field_name]
            if venue_output and fact_appears_in_log(
                v, [ToolCallRecord("venue_search", {}, venue_output)]
            ):
                _pass(field_name, v)
            else:
                _fail(field_name, v)
            break

    for field_name in ("venue_address", "venue-address", "address"):
        if field_name in testid:
            v = testid[field_name]
            if venue_output and fact_appears_in_log(
                v, [ToolCallRecord("venue_search", {}, venue_output)]
            ):
                _pass(field_name, v)
            else:
                _fail(field_name, v)
            break

    # --- Weather facts (must come from get_weather output) ---
    weather_log = [ToolCallRecord("get_weather", {}, weather_output)] if weather_output else []

    conditions_in_flyer = extract_condition_facts(flyer_content)
    for cond in conditions_in_flyer:
        if weather_output and fact_appears_in_log(cond, weather_log):
            _pass("condition", cond)
        else:
            _fail("condition", cond)

    temps_in_flyer = extract_temperature_facts(flyer_content)
    for temp in temps_in_flyer:
        if weather_output and _numeric_fact_appears_in_log(temp, weather_log):
            _pass("temperature_c", temp)
        else:
            _fail("temperature_c", temp)

    # --- Cost facts (must come from calculate_cost output) ---
    testid_values = set(testid.values())

    cost_log = [ToolCallRecord("calculate_cost", {}, cost_output)] if cost_output else []
    money_in_flyer = [m for m in extract_money_facts(flyer_content) if m not in testid_values]
    for amount in money_in_flyer:
        if cost_output and _numeric_fact_appears_in_log(amount, cost_log):
            _pass("cost", amount)
        else:
            _fail("cost", amount)

    # --- Remaining testid facts: check against full log ---
    skip_keys = {
        "venue_name",
        "venue-name",
        "name",
        "venue_address",
        "venue-address",
        "address",
    }
    for key, value in testid.items():
        if key in skip_keys:
            continue
        if fact_appears_in_log(value) or _numeric_fact_appears_in_log(value):
            _pass(key, value)
        else:
            _fail(key, value)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    if unverified:
        return IntegrityResult(
            ok=False,
            unverified_facts=unverified,
            verified_facts=verified,
            summary=(
                f"dataflow FAIL: {len(unverified)} unverified fact(s): "
                f"{unverified[:5]}" + ("..." if len(unverified) > 5 else "")
            ),
        )

    if not verified:
        return IntegrityResult(
            ok=True,
            summary="no extractable facts in flyer (verified vacuously)",
        )

    return IntegrityResult(
        ok=True,
        verified_facts=verified,
        summary=f"dataflow OK: verified {len(verified)} fact(s) against tool outputs",
    )


def load_log_from_file(log_path: str | Path) -> list[ToolCallRecord]:
    """Load tool call log from saved JSON file into _TOOL_CALL_LOG."""
    log_path = Path(log_path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    data = json.loads(log_path.read_text())
    records = [
        ToolCallRecord(
            tool_name=item["tool_name"],
            arguments=item["arguments"],
            output=item["output"],
            timestamp=datetime.fromisoformat(item["timestamp"]),
        )
        for item in data
    ]

    _TOOL_CALL_LOG.clear()
    _TOOL_CALL_LOG.extend(records)
    return records


__all__ = [
    "IntegrityResult",
    "ToolCallRecord",
    "_TOOL_CALL_LOG",
    "clear_log",
    "extract_condition_facts",
    "extract_money_facts",
    "extract_temperature_facts",
    "extract_testid_facts",
    "fact_appears_in_log",
    "load_log_from_file",
    "record_tool_call",
    "verify_dataflow",
]
