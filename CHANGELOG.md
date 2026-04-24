# Changelog

All changes to the homework after a cohort's release tag get documented
here. Students are told to `git pull` when a new entry appears.

Versioning convention:

- **Cohort releases** use `vYYYY.MM.N` (e.g. `v2026.04.0`) and are
  tagged in git. One cohort = one major release.
- **Patch numbers** (`v2026.04.0.N`) increment for fixes shipped during
  a cohort's window.
- **Internal iterations** (`v1` through `v18` in the development log
  below) are NOT released to students; they document the build journey.

---

## [2026.04.0] — unreleased (first cohort, target ship date)

First public release for Nebius Academy Module 1 Week 5. Everything
below represents the state of the homework at the v18 internal
iteration — the final pre-cohort version.

### Architecture delivered

Five exercises extending the sovereign-agent course's agent pattern,
each with a specific pedagogical goal tied to one or more of the
framework's eight architectural decisions:

- **Ex5 — Edinburgh research (loop half).** Four tools +
  `verify_dataflow` integrity check. Teaches: tool-call logging
  (Decision 7), dataflow integrity (Decision 8), HTML as a verifiable
  artefact.
- **Ex6 — Rasa structured half.** Real Rasa Pro CALM flows against
  Nebius Llama-3.3. Teaches: deterministic enforcement at the
  structured half (Decision 6), multi-process coordination, metadata
  as the boundary.
- **Ex7 — Handoff bridge.** Loop-to-structured round-trip with
  reverse handoff on rejection. Teaches: atomic IPC (Decision 5),
  the forward-only state machine (Decision 2), bounded retry.
- **Ex8 — Voice pipeline (bonus).** Real Speechmatics STT + Rime.ai
  Arcana TTS. Teaches: the half-interface abstraction generalises —
  voice is just another I/O mode emitting the same trace events.
- **Ex9 — Reflection (30pt Reasoning layer).** Three written
  questions grounded in session logs. CI grades with LLM-as-judge.

### Framework pin

`sovereign-agent == 0.2.0` exactly (not compatible-release). The
grader depends on trace-event shapes that differ across framework
versions; one pin per cohort is the fair-grading principle.

### Grading structure

Mechanical (27) + Behavioural (19) locally + Reasoning (30) in CI =
100 points total. The 30-point Reasoning layer is outside the scope
of offline `make check-submit`; cohort CI grades it with an
LLM-as-judge rubric.

---

## Development log (internal iterations v1–v18)

Not a changelog students see. A record of what was rebuilt and why,
for the educator team and future iterations.

### v18 — structured `make help` + state-aware `make next`

`make` (default target) now renders a colour-coded, section-organised
walkthrough instead of a flat alphabetical list. New `make next`
inspects repo state and prints the literal next command to run
(walks: venv exists? → `.env` populated? → NEBIUS_KEY set? → which
exercise are you on? → next TODO file to edit).

### v17 — the big reframe

- **`make educator-validate-real` became DIAGNOSTIC.** Always exits 0.
  Produces a report pointing at `docs/real-mode-failures.md`.
  Rationale: Qwen spirals, Rasa caches stale code, voice SDKs glitch —
  these are teaching moments, not bugs to suppress.
- **Real Speechmatics + Rime Arcana voice pipeline** in Ex8 solution.
  Websocket STT, mic capture via sounddevice (with RMS-based VAD),
  Rime REST TTS with pydub MP3 decode and sounddevice playback.
  Graceful degradation when keys or deps are missing.
- **`docs/real-mode-failures.md`** — 8 documented failure modes with
  diagnosis + workaround: Qwen spiral, Rasa action-server cache,
  embeddings-401-from-wrong-YAML-nesting, FakeLLM exhaustion,
  Speechmatics auth, Rime voice rename, mic permission, general
  offline-works-real-breaks patterns.
- **Howard/Raschka-grade README** rewritten from scratch. 400+ lines.
  Opens with the pub story. First hour / First day / First week
  playbook. Every exercise has expected-output examples. Lineage
  section credits fastai, nanoGPT, LLMs-from-scratch, minitorch,
  NanoClaw.
- **`ToolResult(error_code=...)` TypeError** — removed in all six
  error branches; the framework signature doesn't take that kwarg.
- **Starter `voice_loop.py` sanitised** back to a clean TODO stub
  (text-mode complete + `run_voice_mode` TODO with architecture
  diagram in the docstring).

### v16 — Qwen spiral detection + misc

- **Qwen3-32B spiral defense** in Ex5: task prompt tightened with
  HARD RULES ("Do NOT call venue_search more than once"; "Do NOT
  change party_size from 6") plus tool-level spiral detection
  (after 3 calls, `venue_search` returns an error telling the LLM
  to stop). Still doesn't always prevent spiraling — that's OK,
  see v17 reframe.
- **Docker references removed** from cost banner and internal
  lifecycle naming.
- **`make educator-apply-solution` banner** now shows which PID is
  on which port + direct `kill <PID>` command fallback.

### v15 — Ex7 bridge fix

- **HandoffBridge data extraction bug** — the bridge was passing
  the full `handoff_to_structured` args dict (`{reason, context, data}`)
  to the structured half instead of just `data`. Fixed:
  `data=(loop_result.handoff_payload or {}).get("data") or loop_result.output`.
- **Ex7 scripted trajectory** updated: round 2 now uses party=6 so
  mock Rasa approves (demonstrating recovery after round-1 rejection).

### v14 — bridge scripted args fix

- Ex7's `handoff_to_structured` scripted calls were missing the
  required `reason` and `context` kwargs. Added.
- Educator harness's `run_scenario` now scans `trace.jsonl` for
  tool-call failures, not just exit code. Caught cases where
  scenarios exit 0 but had internal tool failures.

### v13 — Rasa flow-syntax cleanup

- **`resume_from_loop` and `request_research` flows deleted.** They
  were dead code — no Python path triggered them, and their
  `collect:` steps required `utter_ask_*` responses we didn't have,
  causing Rasa training to fail. The reverse-handoff in Ex7 lives at
  the Python `HandoffBridge` level, not inside Rasa.
- **flows.yml** reduced to a single `confirm_booking` flow with
  id-labeled steps (`validate`, `rejected`, `confirmed`) for safe
  branching across Rasa CALM versions.

### v12 — Rasa config migration to 3.16+

- Migrated LLM config out of `config.yml` inline block (deprecated,
  removed in Rasa 4) into `endpoints.yml` under `model_groups:` syntax.
- `provider: self-hosted` for the command generator (Nebius LLM),
  `provider: openai` for embeddings (LiteLLM quirk — embeddings path
  only recognises `openai` as the provider tag for OpenAI-compatible
  endpoints).
- Critical fix: **embeddings must be nested under `flow_retrieval:`**
  in `config.yml`, not as a sibling of `llm:`. Wrong nesting causes
  silent fallback to OpenAI embeddings with a 401 against your
  Nebius key.
- Switched command generator to an instruct model
  (`meta-llama/Llama-3.3-70B-Instruct`) — reasoning models emit
  `<think>` tags that break Rasa's command parser.

### v11 — Rasa metadata-vs-slots

- `ActionValidateBooking` rewritten to read
  `tracker.latest_message.metadata.booking` as primary source,
  slots as fallback. Root cause of earlier "internal error" from
  Rasa: CALM starts flows from programmatic triggers like
  `/confirm_booking` but does NOT auto-populate slots from message
  metadata.

### v10 — host-process Rasa

- **Docker-compose for Rasa removed.** Replaced with host-process
  Makefile targets (`make rasa-actions`, `make rasa-serve`) that
  run `rasa run actions` and `rasa run --enable-api` directly in
  the homework's venv. Rationale: `rasa-pro` 3.16 co-installs
  cleanly with `sovereign-agent` 0.2.0 in Python 3.12; Docker was
  an unnecessary second tool to install and troubleshoot.
- `RasaHostLifecycle` async context manager replaces
  `RasaDockerLifecycle` for the auto-spawn tier-3 path.
- Three-tier Ex6 clarified: tier 1 (mock), tier 2 (two terminals,
  probe-and-run), tier 3 (auto-spawn).

### v9 — `make ex6-real` probe-and-run

- `make ex6-real` now probes `localhost:5005` and `localhost:5055`.
  If either service is down, prints a pedagogical banner explaining
  the three-terminal layout ("Terminal 1: `make rasa-actions`", etc.)
  rather than crashing cryptically.
- `docs/rasa-setup.md` added.
- Three-tier Ex6 flow landed in the README.

### v8 — `.env.example` bootstrap + narrator

- Fixed `make setup` crashing with "cp: .env.example: No such file" —
  now prints actionable error and suggests `make env-bootstrap` to
  regenerate from an embedded fallback.
- `scripts/write_env_example.py` ships the fallback content.
- **`scripts/narrator.py`** added — reads any session's
  `logs/trace.jsonl` and renders a human-readable play-by-play with
  tool-specific templates (🔍 venue_search, 💷 calculate_cost, etc.).
  `make narrate SESSION=<id>` and `make narrate-latest`.

### v7 — educator validation harness

- `scripts/educator_validate.py` orchestrates the full
  back-up → apply-solution → run-scenarios → grade → restore cycle.
- `scripts/educator_diagnostics.py` — single comprehensive health
  report: Python/uv/Docker versions, env vars (masked),
  Python deps, service-auth probes (Nebius, Speechmatics, Rime.ai),
  project state. Output is copy-pasteable for debugging.
- `.educator_backup/` as the restore point.
- Solution directory structure (`solution/ex5/`, `solution/ex6/`, etc.)
  for the educator's reference impls.

### v6 — HTML flyer pivot

- Ex5 pivoted from markdown flyer to **HTML flyer** — semantic tags,
  inline CSS, `data-testid="<n>"` attributes for the integrity
  check's DOM parser. Students can open `workspace/flyer.html` in a
  browser and see what their agent actually produced.
- `verify_dataflow` helpers updated: `extract_money_facts` and
  `extract_temperature_facts` strip HTML tags before regex;
  `extract_testid_facts` is the new precision path.

### v5 — grader truthfulness

- **Phantom-point bug fixed.** Pristine scaffold used to score
  ~22/76 before any student effort because the grader ran
  `pytest tests/public/` and reported pass (tests passed via
  `pytest.skip` when TODOs unimplemented). Now: the grader actually
  executes each scenario, checks the trace, and skipped tests don't
  count as passed. Honest pristine score: **4/76**.
- `answers_not_empty` check looks under "Your answer" headings and
  requires ≥40 chars of substance.
- `all_scenarios_have_integrity_check` checks the function body
  isn't just `raise NotImplementedError`, not just that the name
  exists.

### v4 — diagnostic polish

- Rich `educator-diagnostics` output now shows service-auth statuses
  (200 OK from Nebius; 200 from Speechmatics; 400-reachable from
  Rime.ai). Distinguishes "key invalid (401)" from "service
  unreachable" from "auth works but wrong endpoint (404)".

### v3 — nebius_smoke + .env loader

- `scripts/nebius_smoke.py` — 1-token round-trip probe for `make
  verify`. Uses `google/gemma-2-2b-it` (the earlier fast-27b model
  was removed from Nebius in April 2026).
- `scripts/_dotenv.py` — shared `.env` loader. Makefile's
  `include .env && export` idiom handles most cases; this is the
  Python-level fallback.

### v1–v2 — initial scaffolding

- Repo structure established (`starter/`, `answers/`, `rasa_project/`,
  `tests/public/`, `grader/`, `scripts/`, `docs/`).
- Framework pin at `sovereign-agent == 0.2.0`.
- `Makefile` base with `setup`, `verify`, `test`, `check-submit`,
  per-exercise runners.
- CI workflows `ci.yml` (on PR: lint + offline scenarios) and
  `grade.yml` (manual: authoritative grader with secrets).

---

## Unreleased

Entries here will be added if/when a bug fix or clarification lands
during a cohort's active window. Tag convention: `v2026.04.0.1`,
`v2026.04.0.2`, etc.

Future work that is deliberately NOT in v1 of the homework:

- **Ex10 (tentative) — production observability.** Would teach OTel
  export + trace aggregation across halves. Deferred; the
  `trace.jsonl` + `make narrate` workflow is enough for cohort 1.
- **Real voice CI path.** Ex8 voice is currently manual-test-only.
  A future release could record a scripted user audio file and
  exercise Speechmatics in CI.
- **Multi-cohort branching.** When cohort 2 uses a newer
  `sovereign-agent` pin, this repo will branch (`cohort-2026-04`
  frozen, `main` advances).
