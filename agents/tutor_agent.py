"""
PiTutorAgent — Dr. Kini simulation.

Loads its system prompt from prompts/mit-tutor.md. Simulates Dr. Kini,
Supports handoff to InterviewAgent for mock interviews.
"""

import os
import logging

from livekit.agents import Agent, RunContext, function_tool

from config import PROMPTS_DIR
from tools import (
    highlight_text,
    update_content,
    render_visual,
    # start_cognitive_test,
    # update_team_score,
    # get_team_scores,
    write_to_board,
    # update_board_line,
    add_board_block,
    highlight_board_line,
    # insert_board_line,
    # delete_board_line,
    clear_board_content,
)

logger = logging.getLogger("agent-UnlockPi")


def _load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts/ directory."""
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class PiTutorAgent(Agent):
    """
    Dr. Kini simulation agent. Engages as the visionary leader of manipal academy of higher education,
    discussing  education, careers,
    """
    # JUNK: runs cognitive tests, and manages team scores.

    def __init__(self, chat_ctx=None) -> None:
        # Lazy import to avoid circular dependency
        from agents.interview_agent import InterviewAgent  # noqa: F811

        self._interview_agent_cls = InterviewAgent
        self._base_instructions = _load_prompt("mit-tutor.md")

        super().__init__(
            instructions=self._base_instructions,
            chat_ctx=chat_ctx,
            tools=[
                highlight_text,
                update_content,
                render_visual,
                write_to_board,
                # update_board_line,
                add_board_block,
                highlight_board_line,
                # insert_board_line,
                # delete_board_line,
                clear_board_content,
                # start_cognitive_test,
                # update_team_score,
                # get_team_scores,
            ],
        )

    async def on_enter(self):
        """Called when the agent joins. Sends a short greeting."""
        session_data = self.session.userdata
        title = getattr(session_data, "session_title", None)
        topic = getattr(session_data, "session_topic", None)
        goals = getattr(session_data, "session_goals", None)
        structure = getattr(session_data, "session_structure", None)

        if any([title, topic, goals, structure]):
            context_block = (
                "## Current Session Context\n"
                f"Title: {title or ''}\n"
                f"Topic: {topic or ''}\n"
                f"Goals: {goals or ''}\n"
                f"Structure: {structure or ''}"
            )
            await self.update_instructions(f"{self._base_instructions}\n\n{context_block}")

        await self.session.generate_reply(
            instructions="Greet the user, keep it short.",
            allow_interruptions=True,
        )

    # ------------------------------------------------------------------
    # Handoff tool: transfer to interview mode
    # ------------------------------------------------------------------
    @function_tool()
    async def transfer_to_interview(self, context: RunContext):
        """Transfer to interview practice mode when the user wants to practice mock interviews."""
        return self._interview_agent_cls(chat_ctx=self.chat_ctx)
