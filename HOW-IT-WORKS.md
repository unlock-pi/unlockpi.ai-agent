1. `agent.py` boots a LiveKit `AgentServer` and registers one RTC session entrypoint named `UnlockPi`.
2. The `prewarm` hook loads Silero VAD once per worker process to reduce first-user latency.
3. Each room session starts in `entrypoint(ctx)` and immediately creates a Neon async DB pool.
4. Shared mutable session state is stored in `SessionData` and attached as `AgentSession.userdata`.
5. `SessionData` keeps three cores of state: DB pool, cognitive test answers, and board document.
6. Shutdown callbacks close the DB pool so resources are released even on abrupt room teardown.
7. Model selection is centralized in `config.py` via dataclasses for STT, LLM, TTS, and turn detection.
8. Environment variables override defaults, allowing model swaps without touching orchestration logic.
9. STT fallback descriptors are normalized in `helpers/model_fallbacks.py` with language suffix handling.
10. LLM fallback order is built as a deterministic deduplicated chain for resilient completion calls.
11. TTS fallback chain includes voice descriptors so playback can continue across provider failures.
12. The session STT stack uses `inference.STT` with explicit retry and timeout budgets.
13. The LLM stack is wrapped in `llm.FallbackAdapter` with short attempt timeouts for snappy recovery.
14. The TTS stack uses `inference.TTS` and provider fallback models to avoid dead air.
15. Turn detection is selected at runtime between English and multilingual detector plugins.
16. `preemptive_generation=True` enables earlier response generation to reduce perceived wait time.
17. Metrics events are subscribed from session lifecycle and logged for STT, TTS, LLM, and EOU timing.
18. The live agent started in the room is `PiTutorAgent`, defined in `agents/tutor_agent.py`.
19. `PiTutorAgent` loads instruction text from `prompts/mit-tutor.md` at construction time.
20. Agent tools are passed as standalone `@function_tool` callables imported from `tools/`.
21. Tutor tools combine legacy text-board controls and structured board-document operations.
22. `on_enter` in tutor mode emits a concise greeting using `session.generate_reply`.
23. Tutor mode exposes `transfer_to_interview` to hand off conversation control to `InterviewAgent`.
24. `InterviewAgent` loads its own prompt (`prompts/mit-interview.md`) and interview-specific behavior.
25. Interview mode keeps a tighter toolset focused on content updates and board visibility controls.
26. `transfer_to_tutor` returns control back to the tutor persona without losing chat context.
27. Frontend RPC routing relies on `helpers/room_utils.get_frontend_identity()` participant discovery.
28. The preferred frontend identity is `teacher-interface`, with fallback heuristics for single peer rooms.
29. `send_rpc()` serializes payloads and calls LiveKit `perform_rpc` on the local participant.
30. Display tools in `tools/display_tools.py` support `update_content` and `highlight_text` RPCs.
31. `update_content` intentionally resets structured board state to prevent stale dual-mode rendering.
32. Structured board tools in `tools/board_tools.py` operate on a JSON document, not plain markdown.
33. `write_to_board` replaces the full board using a server-side `setBoard` operation.
34. Incremental tools include `update_board_line`, `insert_board_line`, and `delete_board_line`.
35. Block-level edits include `add_board_block` plus line-level semantic highlighting.
36. Every write first mutates backend state through `helpers/board_engine.apply_operation`.
37. The updated operation is then forwarded to frontend via `board_operation` or `set_board` RPC.
38. This backend-first pattern makes Python the source of truth and UI a synchronized projection.
39. `helpers/board_engine.py` mirrors the TypeScript board reducer to keep parity across stacks.
40. Operation handlers are pure and version-bump the document only when a valid mutation occurs.
41. No-op mutations return the previous document, letting tools detect missing IDs safely.
42. `board_to_summary()` generates compact context text for future prompt grounding opportunities.
43. DB helpers are intentionally tolerant: startup continues when Neon is unavailable.
44. That design keeps tutoring, board rendering, and voice flow alive even without persistence.
45. The entrypoint remains thin, while feature complexity is split into agents, tools, and helpers.
46. Prompt files remain external markdown, making persona iteration independent of Python deploys.
47. The architecture supports adding new modes by creating agent classes plus handoff tools.
48. It supports adding new UI abilities by creating function tools that dispatch RPC payloads.
49. LiveKit session plumbing, fallback models, and tool RPC together form the full runtime loop.
50. Net effect: a resilient multimodal tutor agent that speaks, listens, reasons, and drives UI state.
