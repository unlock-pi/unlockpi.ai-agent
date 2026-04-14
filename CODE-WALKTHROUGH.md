# UnlockPi Agent — Deep Code Walkthrough

This document explains the **Python LiveKit agent repo** in depth: startup, session lifecycle, model fallbacks, handoff agents, tools, state model, RPC bridge, and extension points.

---

## 1) High-level architecture

The agent repo is a LiveKit voice agent backend with modular layers:

1. **Entrypoint orchestration** (`agent.py`)
2. **Configuration + model chains** (`config.py`, `helpers/model_fallbacks.py`)
3. **Agent personas + handoffs** (`agents/tutor_agent.py`, `agents/interview_agent.py`)
4. **Tooling surface** (`tools/*.py`)
5. **Shared state + board engine** (`agents/session_data.py`, `helpers/board_engine.py`)
6. **Realtime RPC bridge to frontend** (`helpers/room_utils.py`)
7. **Optional persistence** (`helpers/db.py`)

---

## 2) Runtime startup sequence (`agent.py`)

## 2.1 Process prewarm

- `prewarm(proc)` loads `silero.VAD` once per worker process.
- Reduces first-session startup latency.

## 2.2 Session entrypoint

`@server.rtc_session(agent_name=AGENT_NAME)` registers `entrypoint(ctx)`.

Inside `entrypoint(ctx)`:

1. Create DB pool (`create_db_pool()`).
2. Build `SessionData(db_pool=...)` and attach via `AgentSession.userdata`.
3. Register shutdown callback to close DB pool.
4. Build model fallback chains (`llm_model_chain`, `stt_fallback_descriptors`).
5. Create `AgentSession` with:
   - STT (`inference.STT`)
   - LLM (`llm.FallbackAdapter`)
   - TTS (`inference.TTS`)
   - turn detector (English/Multilingual)
   - VAD + preemptive generation
6. Subscribe metrics callback (`metrics_collected`).
7. `session.start(agent=PiTutorAgent(), room=ctx.room, room_options=...)`.

### Design intent

`agent.py` stays thin and only composes dependencies; business behavior is pushed into agents/tools/helpers.

---

## 3) Configuration model (`config.py`)

`config.py` centralizes all dynamic config via dataclasses:

- `STTConfig`
- `LLMConfig`
- `TTSConfig`
- `TurnDetectionConfig`
- aggregate `ModelConfig` (`models` singleton)

### Key behavior

- Reads env vars with defaults.
- Supports CSV fallback lists via `_csv_env(...)`.
- Provides `PROMPTS_DIR` and `AGENT_NAME`.

### Why important

Model/provider swaps can be done via environment only, without changing orchestration code.

---

## 4) Fallback chain logic (`helpers/model_fallbacks.py`)

Core utility functions:

- `_dedupe(...)`: order-preserving dedupe
- `_append_suffix_if_missing(...)`: append language suffix when STT descriptor lacks one
- `stt_fallback_descriptors(config)`
- `llm_model_chain(config)`
- `tts_model_chain(config)`
- `describe_fallback_chains(...)`

### Runtime effect

- Primary model always stays first.
- Duplicate fallback descriptors are removed.
- STT fallback models get language suffixes consistently.
- TTS chain keeps voice descriptor on primary model.

### Verified by tests

`tests/test_model_fallbacks.py` validates each of these behaviors.

---

## 5) Shared session state model (`agents/session_data.py`)

`SessionData` dataclass stores per-room mutable state:

- `db_pool`
- `current_answers` (cognitive game)
- `board_document` (structured board source of truth)

This object is attached to `AgentSession.userdata` and shared across tool calls and handoffs.

---

## 6) Agent personas and handoffs

## 6.1 Tutor persona (`agents/tutor_agent.py`)

Class: `PiTutorAgent(Agent)`

### Initialization

- Loads instructions from `prompts/mit-tutor.md`.
- Registers tool set:
  - `highlight_text`
  - `update_content`
  - `render_visual`
  - `write_to_board`
  - `add_board_block`
  - `highlight_board_line`
  - `clear_board_content`

### Behavior hooks

- `on_enter()` sends short greeting.
- `transfer_to_interview()` returns `InterviewAgent` as handoff tool.

## 6.2 Interview persona (`agents/interview_agent.py`)

Class: `InterviewAgent(Agent)`

### Initialization

- Loads instructions from `prompts/mit-interview.md`.
- Uses narrower toolset (`update_content`, `render_visual`, `write_to_board`, `clear_board_content`).

### Behavior hooks

- `on_enter()` sets interview context and asks readiness.
- `transfer_to_tutor()` hands back to `PiTutorAgent`.

### Why this split matters

Separate personas reduce tool/prompt overload and keep each mode more deterministic.

---

## 7) RPC bridge layer (`helpers/room_utils.py`)

Two critical functions:

1. `get_frontend_identity()`
   - Finds frontend participant identity in room.
   - Prefers `teacher-interface`, then heuristics (`teacher` / `frontend`), then single-peer fallback.

2. `send_rpc(method, payload, timeout, frontend_id)`
   - Serializes payload.
   - Calls `room.local_participant.perform_rpc(...)`.
   - Returns raw response string.

### Why this abstraction exists

Every tool can dispatch frontend updates without duplicating participant lookup and RPC boilerplate.

---

## 8) Tool surface by category

## 8.1 Display tools (`tools/display_tools.py`)

### `highlight_text(context, words)`

- Parses word/type list JSON.
- Sends RPC `highlight_text` with `{"action":"highlight", ...}` payload.
- Returns summary by type count.

### `update_content(context, text)`

- Clears structured board in session state (`create_empty_board()`) to avoid stale mixed mode.
- Sends RPC `update_content` with plain text.

## 8.2 Structured board tools (`tools/board_tools.py`)

These tools mutate backend board state first, then broadcast operation/full document to frontend.

- `write_to_board(...)` → replaces full board (`setBoard`)
- `update_board_line(...)`
- `add_board_block(...)`
- `highlight_board_line(...)`
- `insert_board_line(...)`
- `delete_board_line(...)`
- `clear_board_content(...)`

### Pattern used

1. Read `context.userdata.board_document`
2. Apply operation through `helpers/board_engine.apply_operation(...)`
3. Save updated doc back into userdata
4. Send RPC (`board_operation`, `set_board`, or `clear_board`)

This keeps Python as authoritative board state manager.

## 8.3 Visual schema tool (`tools/visual_tools.py`)

### `render_visual(context, visual_json)`

- Validates strict schemas for:
  - `map`
  - `chart`
  - `flow`
  - `graph`
- Normalizes wrapper forms (`{type,data}` vs direct)
- Enforces allowed keys and value types
- Sends RPC `render_visual`

### Value

Prevents malformed visual payloads from reaching frontend renderer.

## 8.4 Game tools (`tools/game_tools.py`)

### `start_cognitive_test(context, question, answers)`

- Parses answer JSON array.
- Stores parsed answers in `context.userdata.current_answers`.
- Sends RPC `start_cognitive_test`.

`check_cognitive_answer` exists as commented scaffold for future answer reveal flow.

## 8.5 Score tools (`tools/score_tools.py`)

- `_sync_scores_to_frontend(...)`
- `update_team_score(context, team_name, points)`
- `get_team_scores(context)`

These depend on DB availability and sync scores via `update_scores` RPC.

---

## 9) Structured board engine (`helpers/board_engine.py`)

This is a pure reducer-like module mirroring frontend board logic.

### Public functions

- `create_empty_board()`
- `apply_operation(doc, op)`
- `board_to_summary(doc)`

### Supported operation types

- `updateLine`
- `insertLineAfter`
- `deleteLine`
- `addBlock`
- `deleteBlock`
- `highlightLine`
- `setBoard`

### Important behavior

- Invalid operations are no-ops returning original doc.
- Valid operations return bumped `version`.
- Pure function style keeps mutation logic deterministic and testable.

---

## 10) Database layer (`helpers/db.py`)

- `create_db_pool()`
  - Returns `None` if env missing or connection fails.
- `close_db_pool(pool)`
  - Safe cleanup during shutdown.

### Architectural note

DB is optional for runtime continuity; voice tutoring still works when DB is unavailable.

---

## 11) End-to-end request and response flow

## 11.1 Voice turn

1. User speaks in web frontend.
2. Audio track reaches LiveKit room.
3. Agent STT transcribes.
4. LLM decides response + optional tool call.
5. TTS generates spoken response.
6. Audio returns to frontend.

## 11.2 Tool-triggered UI mutation

1. LLM invokes tool (e.g., `write_to_board`).
2. Tool updates backend session state.
3. Tool sends RPC to frontend participant.
4. Frontend RPC handler applies UI change.

## 11.3 Persona handoff

1. User requests interview mode.
2. Tutor invokes `transfer_to_interview`.
3. LiveKit framework swaps active agent class.
4. Shared userdata persists across handoff.

---

## 12) Reliability controls in current design

1. Prewarmed VAD for lower first-turn latency.
2. STT/LLM/TTS fallback chains to reduce provider outage impact.
3. Optional DB dependency model (graceful degradation).
4. Room shutdown callback to close resources.
5. Strict schema validation for visual payload safety.
6. Backend-first board mutation model for consistency.

---

## 13) Fast onboarding map (read in this order)

1. `agent.py`
2. `config.py`
3. `agents/session_data.py`
4. `agents/tutor_agent.py`
5. `agents/interview_agent.py`
6. `helpers/room_utils.py`
7. `tools/display_tools.py`
8. `tools/board_tools.py`
9. `helpers/board_engine.py`
10. `helpers/model_fallbacks.py` + `tests/test_model_fallbacks.py`

---

## 14) Common extension patterns

## Add a new tool

1. Create `tools/<new_tool>.py`.
2. Implement `@function_tool` function.
3. Re-export via `tools/__init__.py` if needed.
4. Add tool to the target agent’s `tools=[...]` list.

## Add a new persona/mode

1. Add new `agents/<mode>_agent.py` class.
2. Add prompt file under `prompts/`.
3. Define handoff function tools between modes.
4. Keep state in `SessionData` if cross-mode continuity is needed.

## Add a new board operation

1. Extend `helpers/board_engine.py` operation dispatcher.
2. Add tool wrapper in `tools/board_tools.py`.
3. Ensure frontend RPC handler supports operation.
4. Keep TS and Python board engines behaviorally aligned.

---

## 15) Important implementation cautions

1. Keep prompt loading external (`prompts/*.md`) rather than hardcoding in classes.
2. Preserve `AgentSession.userdata` pattern for shared mutable state.
3. Avoid bypassing `send_rpc(...)` helper to keep participant targeting consistent.
4. Keep board engine pure; avoid side effects in reducer functions.
5. Maintain parity between Python and frontend board operation semantics.

---

This repo is already structured for scale: entrypoint orchestration is thin, tool surface is modular, state is explicit, and handoffs keep mode complexity manageable.