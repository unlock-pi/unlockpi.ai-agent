"""
Shared session state — attached to AgentSession[SessionData].userdata.

Follows LiveKit's recommended userdata pattern
(see: https://docs.livekit.io/agents/logic/agents-handoffs/#passing-state).
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import asyncpg

from helpers.board_engine import create_empty_board


@dataclass
class SessionData:
    """Mutable state shared across agents and tools within a single session."""

    db_pool: Optional[asyncpg.Pool] = None

    # Game state for cognitive tests (Family Feud)
    current_answers: list[dict[str, Any]] = field(default_factory=list)

    # Structured board document — source of truth for the board
    board_document: dict = field(default_factory=create_empty_board)

    # Teaching session context loaded from Supabase (optional)
    session_title: str | None = None
    session_topic: str | None = None
    session_goals: str | None = None
    session_structure: str | None = None
