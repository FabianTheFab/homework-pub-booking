# Ex9 — Reflection

## Q1 — Handoff decision in Ex7 logs

### Your answer

In both Ex7 sessions the planner never assigned `assigned_half: "structured"` directly — it consistently produced `assigned_half: "loop"`. The handoff was triggered by the executor calling the `handoff_to_structured` tool, which the bridge detected via `loop_result.next_action == "handoff_to_structured"`.

The clearest evidence is in `sess_23d7847b6ed4` (fake mode). `round_1_forward.json` shows the executor passing `venue_id: "Haymarket Tap"`, `party_size: 12` to the structured half after completing `venue_search`. That tool call was the signal - not a planner decision.

This is worth noting because the framework supports two handoff mechanisms: the planner assigning `assigned_half: "structured"`, or the executor calling `handoff_to_structured` mid-execution. Ex7 uses the latter exclusively, seemingly by design.

## Q2 — Dataflow integrity check in Ex5

### Your answer

The integrity check did not trigger during the clean run (`sess_fda414fa6e1b`) because all facts in `flyer.html` traced directly to tool outputs in `tool_call_log.json`. The earlier session `sess_5f24ebaf53c4` - run without system prompts - shows what it is designed to catch: the planner went off-plan and the executor invented data rather than calling tools in sequence.

A concrete plausible scenario: the LLM calls `get_weather` and receives `temperature_c: 12`, but passes `temperature_c: 14` to `generate_flyer`. A human reviewer looking at a well-formatted flyer showing "14°C" has no reason for suspicion. The integrity check compares every fact in the flyer against `_TOOL_CALL_LOG` entries and flags the discrepancy immediately. This class of quiet substitution is undetectable by manual review but trivially caught by the check.

## Q3 — First production failure

### Your answer

If the loop produces a valid-looking handoff that Rasa rejects every round, the bridge exhausts `max_rounds=3` and returns `outcome="max_rounds_exceeded"` with `summary="bridge exhausted 3 rounds without resolution"`. The session is marked failed, but the stored result contains no trace of what Rasa's rejection reason was across the rounds. The individual `HalfResult` objects are not persisted, and only the final bridge outcome is written to `session.json`.

This is evidenced by the early real-mode runs before the prompt fixes, where the bridge hit max_rounds with no useful diagnostic. The `round_N_reverse.json` files in `handoffs_audit/` record the rejection reason per round, but only if the bridge actually wrote them, which it does not on the final round before giving up, since there is no further loop to hand back to.

The fix would be for the bridge to write the final structured result to `handoffs_audit/` unconditionally before returning `max_rounds_exceeded`, so post-mortem analysis has the full rejection chain rather than just the outcome string.

## Citations

- evidence/ex7/sess_23d7847b6ed4 — round_1_forward.json, round_1_reverse.json
- evidence/ex7/sess_6a8356250748 — session.json
- evidence/ex5/sess_fda414fa6e1b — tool_call_log.json, flyer.html
- evidence/ex5/sess_5f24ebaf53c4 — session.json