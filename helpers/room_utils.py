"""
Room utilities — helpers for finding participants and sending RPC commands.

Extracted from the monolithic agent.py so every tool module can share
the same logic without duplicating the boilerplate.
"""

import json
import logging
from typing import Any

from livekit.agents import get_job_context

logger = logging.getLogger("agent-UnlockPi")


# ---------------------------------------------------------------------------
# Find the frontend participant
# ---------------------------------------------------------------------------
def get_frontend_identity() -> str | None:
    """
    Finds the frontend participant identity in the current room.
    The frontend joins as 'teacher-interface' (set in classroom/page.tsx).
    Returns None if no matching participant is found.
    """
    try:
        room = get_job_context().room
        for identity in room.remote_participants:
            if identity.lower() == "teacher-interface":
                return identity

        for identity in room.remote_participants:
            lowered = identity.lower()
            if "teacher" in lowered or "frontend" in lowered:
                return identity

        remote_ids = list(room.remote_participants.keys())
        if len(remote_ids) == 1:
            return remote_ids[0]

        logger.warning(
            "Could not uniquely identify frontend participant. Remote identities: %s",
            remote_ids,
        )
    except Exception as e:
        logger.warning(f"Could not find frontend participant: {e}")
    return None


# ---------------------------------------------------------------------------
# Generic RPC sender
# ---------------------------------------------------------------------------
async def send_rpc(
    method: str,
    payload: dict[str, Any] | str,
    *,
    timeout: float = 10.0,
    frontend_id: str | None = None,
) -> str:
    """
    Send an RPC call to the frontend participant.

    Args:
        method: The RPC method name registered on the frontend.
        payload: Dict (will be JSON-serialised) or pre-serialised JSON string.
        timeout: Response timeout in seconds.
        frontend_id: Override auto-detection of the frontend participant.

    Returns:
        The raw response string from the frontend.

    Raises:
        RuntimeError: When no frontend participant can be found.
        Exception: Propagated from the underlying RPC call.
    """
    target = frontend_id or get_frontend_identity()
    if not target:
        raise RuntimeError("Could not find the classroom display participant.")

    payload_str = json.dumps(payload) if isinstance(payload, dict) else payload

    room = get_job_context().room
    response = await room.local_participant.perform_rpc(
        destination_identity=target,
        method=method,
        payload=payload_str,
        response_timeout=timeout,
    )
    return response
