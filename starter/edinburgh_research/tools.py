"""Ex5 tools. Four tools the agent uses to research an Edinburgh booking.

Each tool:
  1. Reads its fixture from sample_data/ (DO NOT modify the fixtures).
  2. Logs its arguments and output into _TOOL_CALL_LOG (see integrity.py).
  3. Returns a ToolResult with success=True/False, output=dict, summary=str.

The grader checks for:
  * Correct parallel_safe flags (reads True, generate_flyer False).
  * Every tool's results appear in _TOOL_CALL_LOG.
  * Tools fail gracefully on missing fixtures or bad inputs (ToolError,
    not RuntimeError).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from sovereign_agent.errors import ToolError
from sovereign_agent.session.directory import Session
from sovereign_agent.tools.registry import ToolRegistry, ToolResult, _RegisteredTool

from starter.edinburgh_research.integrity import (
    _TOOL_CALL_LOG,
    record_tool_call,
)

_SAMPLE_DATA = Path(__file__).parent / "sample_data"


# ---------------------------------------------------------------------------
# TODO 1 — venue_search
# ---------------------------------------------------------------------------
def venue_search(near: str, party_size: int, budget_max_gbp: int = 1000) -> ToolResult:
    """Search for Edinburgh venues near <near> that can seat the party.

    Reads sample_data/venues.json. Filters by:
      * open_now == True
      * area contains <near> (case-insensitive substring match)
      * seats_available_evening >= party_size
      * hire_fee_gbp + min_spend_gbp <= budget_max_gbp

    Returns a ToolResult with:
      output: {"near": ..., "party_size": ..., "results": [<venue dicts>], "count": int}
      summary: "venue_search(<near>, party=<N>): <count> result(s)"

    MUST call record_tool_call(...) before returning so the integrity
    check can see what data was produced.
    """
    # TODO 1a: load venues.json. Raise ToolError(SA_TOOL_DEPENDENCY_MISSING)
    #          if the file is absent.

    arguments = {
        "near": near,
        "party_size": party_size,
        "budget_max_gbp": budget_max_gbp,
    }

    try:
        # Validate inputs
        if not isinstance(near, str):
            raise ToolError(code="SA_TOOL_INVALID_INPUT", message="'near' must be a string")

        if not isinstance(party_size, int) or party_size <= 0:
            raise ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message="'party_size' must be a positive integer",
            )

        if not isinstance(budget_max_gbp, int) or budget_max_gbp < 0:
            raise ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message="'budget_max_gbp' must be a non-negative integer",
            )

        # Load venues.json fixture
        fixture_path = _SAMPLE_DATA / "venues.json"

        if not os.path.exists(fixture_path):
            raise ToolError(code="SA_TOOL_DEPENDENCY_MISSING", message=f"{fixture_path} not found")

        try:
            with open(fixture_path) as f:
                venues = json.load(f)
        except json.JSONDecodeError as e:
            raise ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message=f"Invalid JSON in {fixture_path}: {e}",
            ) from e
        except Exception as e:
            raise ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message=f"Failed to read {fixture_path}: {e}",
            ) from e

        search_count = sum(1 for r in _TOOL_CALL_LOG if r.tool_name == "venue_search")
        if search_count >= 3:
            return ToolResult(
                success=False,
                output={"error": "too_many_searches", "count": search_count},
                summary="STOP calling venue_search; use the results you already have.",
            )

        # Filter venues
        near_lower = near.lower().strip()
        filtered_venues = []

        for venue in venues:
            # Check all filtering criteria
            if not venue.get("open_now", False):
                continue

            # Case-insensitive substring match on area (skip if near is empty)
            if near_lower:
                area = venue.get("area", "")
                if near_lower not in area.lower():
                    continue

            # Check capacity
            seats = venue.get("seats_available_evening", 0)
            if seats < party_size:
                continue

            # Check budget
            hire_fee = venue.get("hire_fee_gbp", 0)
            min_spend = venue.get("min_spend_gbp", 0)
            total_cost = hire_fee + min_spend
            if total_cost > budget_max_gbp:
                continue

            # All criteria met
            filtered_venues.append(venue)

        # Prepare output
        output = {
            "near": near,
            "party_size": party_size,
            "results": filtered_venues,
            "count": len(filtered_venues),
        }

        summary = f"venue_search({near}, party={party_size}): {len(filtered_venues)} result(s)"

        result = ToolResult(success=True, output=output, summary=summary)

        # Log the tool call
        record_tool_call("venue_search", arguments, result.output)

        return result

    except ToolError:
        # Re-raise ToolErrors as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        error_result = ToolResult(
            success=False,
            output={"error": str(e)},
            summary=f"venue_search failed: {str(e)}",
        )
        record_tool_call("venue_search", arguments, error_result.output)
        raise ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"Unexpected error in venue_search: {e}",
        ) from e


# ---------------------------------------------------------------------------
# TODO 2 — get_weather
# ---------------------------------------------------------------------------
def get_weather(city: str, date: str) -> ToolResult:
    """Look up the scripted weather for <city> on <date> (YYYY-MM-DD).

    Reads sample_data/weather.json. Returns:
      output: {"city": str, "date": str, "condition": str, "temperature_c": int, ...}
      summary: "get_weather(<city>, <date>): <condition>, <temp>C"

    If the city or date is not in the fixture, return success=False with
    a clear ToolError (SA_TOOL_INVALID_INPUT). Do NOT raise.

    MUST call record_tool_call(...) before returning.
    """
    arguments = {"city": city, "date": date}

    try:
        # Load weather.json fixture
        fixture_path = _SAMPLE_DATA / "weather.json"

        if not os.path.exists(fixture_path):
            raise ToolError(code="SA_TOOL_DEPENDENCY_MISSING", message=f"{fixture_path} not found")

        try:
            with open(fixture_path) as f:
                weather_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message=f"Invalid JSON in {fixture_path}: {e}",
            ) from e
        except Exception as e:
            raise ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message=f"Failed to read {fixture_path}: {e}",
            ) from e

        # Normalize city name to lowercase for lookup
        city_lower = city.lower()

        # Check if city exists in the data
        if city_lower not in weather_data:
            output = {
                "city": city,
                "date": date,
                "error": f"City '{city}' not found in weather data",
            }
            summary = f"get_weather({city}, {date}): city not found"
            result = ToolResult(success=False, output=output, summary=summary)
            record_tool_call("get_weather", arguments, result.output)
            return result

        # Check if date exists for this city
        city_weather = weather_data[city_lower]
        if date not in city_weather:
            output = {
                "city": city,
                "date": date,
                "error": f"Date '{date}' not found for city '{city}'",
            }
            summary = f"get_weather({city}, {date}): date not found"
            result = ToolResult(success=False, output=output, summary=summary)
            record_tool_call("get_weather", arguments, result.output)
            return result

        # Get weather data for the specified date
        weather = city_weather[date]

        # Prepare output with all weather fields
        output = {
            "city": city,
            "date": date,
            "condition": weather["condition"],
            "temperature_c": weather["temperature_c"],
            "precip_mm": weather["precip_mm"],
            "wind_kph": weather["wind_kph"],
        }

        summary = (
            f"get_weather({city}, {date}): {weather['condition']}, {weather['temperature_c']}C"
        )

        result = ToolResult(success=True, output=output, summary=summary)

        # Log the tool call
        record_tool_call("get_weather", arguments, result.output)

        return result

    except ToolError:
        # Re-raise ToolErrors as-is (only for missing fixture file)
        raise
    except Exception as e:
        # Wrap unexpected errors
        error_result = ToolResult(
            success=False,
            output={"city": city, "date": date, "error": str(e)},
            summary=f"get_weather failed: {str(e)}",
        )
        record_tool_call("get_weather", arguments, error_result.output)
        raise ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"Unexpected error in get_weather: {e}",
        ) from e


# ---------------------------------------------------------------------------
# TODO 3 — calculate_cost
# ---------------------------------------------------------------------------
def calculate_cost(
    venue_id: str,
    party_size: int,
    duration_hours: int,
    catering_tier: str = "bar_snacks",
) -> ToolResult:
    """Compute the total cost for a booking.

    Formula:
      base_per_head = base_rates_gbp_per_head[catering_tier]
      venue_mult    = venue_modifiers[venue_id]
      subtotal      = base_per_head * venue_mult * party_size * max(1, duration_hours)
      service       = subtotal * service_charge_percent / 100
      total         = subtotal + service + <venue's hire_fee_gbp + min_spend_gbp>
      deposit_rule  = per deposit_policy thresholds

    Returns:
      output: {
        "venue_id": str,
        "party_size": int,
        "duration_hours": int,
        "catering_tier": str,
        "subtotal_gbp": int,
        "service_gbp": int,
        "total_gbp": int,
        "deposit_required_gbp": int,
      }
      summary: "calculate_cost(<venue>, <party>): total £<N>, deposit £<M>"

    MUST call record_tool_call(...) before returning.
    """
    # Store arguments for logging
    arguments = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
    }

    try:
        # Load catering.json fixture
        catering_path = _SAMPLE_DATA / "catering.json"
        if not os.path.exists(catering_path):
            raise ToolError(code="SA_TOOL_DEPENDENCY_MISSING", message=f"{catering_path} not found")

        try:
            with open(catering_path) as f:
                catering_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message=f"Invalid JSON in {catering_path}: {e}",
            ) from e

        # Load venues.json fixture (needed for hire_fee and min_spend)
        venues_path = _SAMPLE_DATA / "venues.json"
        if not os.path.exists(venues_path):
            raise ToolError(code="SA_TOOL_DEPENDENCY_MISSING", message=f"{venues_path} not found")

        try:
            with open(venues_path) as f:
                venues_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ToolError(
                code="SA_TOOL_DEPENDENCY_MISSING",
                message=f"Invalid JSON in {venues_path}: {e}",
            ) from e

        # Validate catering tier
        base_rates = catering_data["base_rates_gbp_per_head"]
        if catering_tier not in base_rates:
            raise ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"Invalid catering_tier '{catering_tier}'. Must be one of: {list(base_rates.keys())}",
            )

        # Validate venue_id
        venue_modifiers = catering_data["venue_modifiers"]
        if venue_id not in venue_modifiers:
            raise ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"Invalid venue_id '{venue_id}'. Must be one of: {list(venue_modifiers.keys())}",
            )

        # Find venue in venues data
        venue = None
        for v in venues_data:
            if v["id"] == venue_id:
                venue = v
                break

        if venue is None:
            raise ToolError(
                code="SA_TOOL_INVALID_INPUT",
                message=f"Venue '{venue_id}' not found in venues.json",
            )

        # Calculate costs
        base_per_head = base_rates[catering_tier]
        venue_mult = venue_modifiers[venue_id]
        hours = max(1, duration_hours)

        # Subtotal = base_per_head * venue_mult * party_size * hours
        subtotal = base_per_head * venue_mult * party_size * hours

        # Service charge
        service_charge_percent = catering_data["service_charge_percent"]
        service = subtotal * service_charge_percent / 100

        # Add venue fees
        hire_fee = venue["hire_fee_gbp"]

        # Total
        total = subtotal + service + hire_fee

        # Determine deposit based on policy
        if total < 300:
            deposit_required = 0
        elif total <= 1000:
            deposit_required = int(total * 0.20)
        else:
            deposit_required = int(total * 0.30)

        # Prepare output (convert floats to ints for final values)
        output = {
            "venue_id": venue_id,
            "party_size": party_size,
            "duration_hours": duration_hours,
            "catering_tier": catering_tier,
            "subtotal_gbp": int(subtotal),
            "service_gbp": int(service),
            "total_gbp": int(total),
            "deposit_required_gbp": deposit_required,
        }

        summary = f"calculate_cost({venue_id}, {party_size}): total £{int(total)}, deposit £{deposit_required}"

        result = ToolResult(success=True, output=output, summary=summary)

        # Log the tool call
        record_tool_call("calculate_cost", arguments, result.output)

        return result

    except ToolError:
        raise
    except Exception as e:
        error_result = ToolResult(
            success=False,
            output={"error": str(e)},
            summary=f"calculate_cost failed: {str(e)}",
        )
        record_tool_call("calculate_cost", arguments, error_result.output)
        raise ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"Unexpected error in calculate_cost: {e}",
        ) from e


# ---------------------------------------------------------------------------
# TODO 4 — generate_flyer
# ---------------------------------------------------------------------------
def generate_flyer(session: Session, event_details: dict) -> ToolResult:
    """Produce an HTML flyer and write it to workspace/flyer.html.

    event_details is expected to contain at least:
      venue_name, venue_address, date, time, party_size, condition,
      temperature_c, total_gbp, deposit_required_gbp

    Write a self-contained HTML flyer (inline CSS, no external assets). Tag every key fact with data-testid="<n>" so the integrity check can parse it.

    Write a formatted HTML flyer with an H1 title, the event
    facts, a weather summary, and the cost breakdown.

    Returns:
      output: {"path": "workspace/flyer.html", "bytes_written": int}
      summary: "generate_flyer: wrote <path> (<N> chars)"

    MUST call record_tool_call(...) before returning — the integrity
    check compares the flyer's contents against earlier tool outputs.

    IMPORTANT: this tool MUST be registered with parallel_safe=False
    because it writes a file.
    """
    arguments = {"event_details": event_details}

    try:
        # Extract event details with defaults
        venue_name = event_details.get("venue_name", "Unknown Venue")
        venue_address = event_details.get("venue_address", "Address not provided")
        date = event_details.get("date", "TBD")
        time = event_details.get("time", "TBD")
        party_size = event_details.get("party_size", 0)
        condition = event_details.get("condition", "N/A")
        temperature_c = event_details.get("temperature_c", 0)
        total_gbp = event_details.get("total_gbp", 0)
        deposit_required_gbp = event_details.get("deposit_required_gbp", 0)

        # Generate HTML flyer
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Flyer - {venue_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }}

        .flyer {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}

        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .subtitle {{
            font-size: 1.2em;
            opacity: 0.95;
        }}

        .content {{
            padding: 40px 30px;
        }}

        .section {{
            margin-bottom: 30px;
            padding-bottom: 30px;
            border-bottom: 2px solid #f0f0f0;
        }}

        .section:last-child {{
            border-bottom: none;
        }}

        h2 {{
            color: #667eea;
            font-size: 1.5em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }}

        h2::before {{
            content: '';
            display: inline-block;
            width: 4px;
            height: 24px;
            background: #667eea;
            margin-right: 10px;
            border-radius: 2px;
        }}

        .detail-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            font-size: 1.1em;
        }}

        .detail-label {{
            font-weight: 600;
            color: #555;
        }}

        .detail-value {{
            color: #222;
            font-weight: 500;
        }}

        .weather-badge {{
            display: inline-block;
            padding: 8px 16px;
            background: #e3f2fd;
            color: #1976d2;
            border-radius: 20px;
            font-weight: 600;
            font-size: 1em;
        }}

        .cost-highlight {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 10px;
            margin-top: 15px;
        }}

        .cost-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            font-size: 1.1em;
        }}

        .total-row {{
            font-size: 1.4em;
            font-weight: 700;
            color: #667eea;
            border-top: 2px solid #ddd;
            padding-top: 15px;
            margin-top: 10px;
        }}

        .footer {{
            background: #f9f9f9;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 0.95em;
        }}
    </style>
</head>
<body>
    <div class="flyer">
        <div class="header">
            <h1 data-testid="venue_name">{venue_name}</h1>
            <p class="subtitle">You're Invited!</p>
        </div>

        <div class="content">
            <div class="section">
                <h2>Event Details</h2>
                <div class="detail-row">
                    <span class="detail-label">Date:</span>
                    <span class="detail-value" data-testid="date">{date}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time:</span>
                    <span class="detail-value" data-testid="time">{time}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Party Size:</span>
                    <span class="detail-value" data-testid="party_size">{party_size}</span>
                </div>
            </div>

            <div class="section">
                <h2>Venue</h2>
                <div class="detail-row">
                    <span class="detail-label">Location:</span>
                    <span class="detail-value" data-testid="venue_address">{venue_address}</span>
                </div>
            </div>

            <div class="section">
                <h2>Weather Forecast</h2>
                <div class="detail-row">
                    <span class="detail-label">Conditions:</span>
                    <span class="weather-badge" data-testid="condition">{condition}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Temperature:</span>
                    <span class="detail-value" data-testid="temperature_c">{temperature_c}°C</span>
                </div>
            </div>

            <div class="section">
                <h2>Cost Breakdown</h2>
                <div class="cost-highlight">
                    <div class="cost-row total-row">
                        <span>Total Cost:</span>
                        <span data-testid="total_gbp">£{total_gbp}</span>
                    </div>
                    <div class="cost-row">
                        <span>Deposit Required:</span>
                        <span data-testid="deposit_required_gbp">£{deposit_required_gbp}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>Looking forward to seeing you there!</p>
        </div>
    </div>
</body>
</html>
"""

        # Write to file
        path = session.workspace_dir / "flyer.html"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

        bytes_written = len(html_content)

        output = {"path": str(path), "bytes_written": bytes_written}

        summary = f"generate_flyer: wrote {path} ({bytes_written} chars)"

        result = ToolResult(success=True, output=output, summary=summary)

        # Log the tool call
        record_tool_call("generate_flyer", arguments, result.output)

        return result

    except Exception as e:
        error_result = ToolResult(
            success=False,
            output={"error": str(e)},
            summary=f"generate_flyer failed: {str(e)}",
        )
        record_tool_call("generate_flyer", arguments, error_result.output)
        raise ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"Unexpected error in generate_flyer: {e}",
        ) from e


# ---------------------------------------------------------------------------
# Registry builder — DO NOT MODIFY the name, signature, or registration calls.
# The grader imports and calls this to pick up your tools.
# ---------------------------------------------------------------------------
def build_tool_registry(session: Session) -> ToolRegistry:
    """Build a session-scoped tool registry with all four Ex5 tools plus
    the sovereign-agent builtins (read_file, write_file, list_files,
    handoff_to_structured, complete_task).

    DO NOT change the tool names — the tests and grader call them by name.
    """
    from sovereign_agent.tools.builtin import make_builtin_registry

    reg = make_builtin_registry(session)

    # venue_search
    reg.register(
        _RegisteredTool(
            name="venue_search",
            description="Search Edinburgh venues by area, party size, and max budget.",
            fn=venue_search,
            parameters_schema={
                "type": "object",
                "properties": {
                    "near": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "budget_max_gbp": {"type": "integer", "default": 1000},
                },
                "required": ["near", "party_size"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {
                        "near": "Haymarket",
                        "party_size": 6,
                        "budget_max_gbp": 800,
                    },
                    "output": {"count": 1, "results": [{"id": "haymarket_tap"}]},
                }
            ],
        )
    )

    # get_weather
    reg.register(
        _RegisteredTool(
            name="get_weather",
            description="Get scripted weather for a city on a YYYY-MM-DD date.",
            fn=get_weather,
            parameters_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["city", "date"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"city": "Edinburgh", "date": "2026-04-25"},
                    "output": {"condition": "cloudy", "temperature_c": 12},
                }
            ],
        )
    )

    # calculate_cost
    reg.register(
        _RegisteredTool(
            name="calculate_cost",
            description="Compute total cost and deposit for a booking.",
            fn=calculate_cost,
            parameters_schema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                    "catering_tier": {
                        "type": "string",
                        "enum": [
                            "drinks_only",
                            "bar_snacks",
                            "sit_down_meal",
                            "three_course_meal",
                        ],
                        "default": "bar_snacks",
                    },
                },
                "required": ["venue_id", "party_size", "duration_hours"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # pure compute, no shared state
            examples=[
                {
                    "input": {
                        "venue_id": "haymarket_tap",
                        "party_size": 6,
                        "duration_hours": 3,
                    },
                    "output": {"total_gbp": 540, "deposit_required_gbp": 0},
                }
            ],
        )
    )

    # generate_flyer — parallel_safe=False because it writes a file
    def _flyer_adapter(event_details: dict) -> ToolResult:
        return generate_flyer(session, event_details)

    reg.register(
        _RegisteredTool(
            name="generate_flyer",
            description="Write an HTML flyer for the event to workspace/flyer.html.",
            fn=_flyer_adapter,
            parameters_schema={
                "type": "object",
                "properties": {"event_details": {"type": "object"}},
                "required": ["event_details"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=False,  # writes a file — MUST be False
            examples=[
                {
                    "input": {
                        "event_details": {
                            "venue_name": "Haymarket Tap",
                            "date": "2026-04-25",
                            "party_size": 6,
                        }
                    },
                    "output": {"path": "workspace/flyer.html"},
                }
            ],
        )
    )

    return reg


__all__ = [
    "build_tool_registry",
    "venue_search",
    "get_weather",
    "calculate_cost",
    "generate_flyer",
]
