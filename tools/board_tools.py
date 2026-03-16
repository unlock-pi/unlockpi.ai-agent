"""
Board tools — structured board operations via RPC.

These are standalone @function_tool functions for the new structured board system.
The board is a document tree (BoardDocument → Block[] → Line[]).
Operations are applied on the backend (source of truth) then broadcast to the frontend via RPC.
"""

import json
import logging

from livekit.agents import RunContext, function_tool

from helpers.room_utils import get_frontend_identity, send_rpc
from helpers.board_engine import apply_operation, board_to_summary, create_empty_board

logger = logging.getLogger("agent-UnlockPi")


# ── Helpers ───────────────────────────────────────────────────────────

def _get_board(context: RunContext) -> dict:
    """Get the current board document from session state."""
    return context.userdata.board_document


def _set_board(context: RunContext, doc: dict) -> None:
    """Update the board document in session state."""
    context.userdata.board_document = doc


async def _send_board_op(op: dict, frontend_id: str) -> None:
    """Send a single board operation to the frontend."""
    await send_rpc("board_operation", json.dumps(op), frontend_id=frontend_id)


# ── Tools ─────────────────────────────────────────────────────────────

@function_tool()
async def write_to_board(
    context: RunContext,
    board_json: str,
) -> str:
    """Write structured content to the classroom board. Replaces the entire board.

    Call this when you need to display NEW content on the board (paragraphs, formulas, diagrams).
    The board uses a structured document model — NOT markdown.

    Args:
        board_json: A JSON string containing a BoardDocument object with this structure:
            {
              "id": "board-1",
              "version": 1,
              "blocks": [
                {
                  "id": "block-1",
                  "type": "paragraph",
                  "lines": [
                    { "id": "l1", "text": "First line of text." },
                    { "id": "l2", "text": "Second line.", "highlight": "definition" }
                  ]
                },
                {
                  "id": "block-2",
                  "type": "formula",
                  "formula": "E=mc^2"
                },
                {
                  "id": "block-3",
                  "type": "diagram",
                  "diagramType": "mermaid",
                  "content": "flowchart TD\\n  A[\"Start\"] --> B[\"End\"]"
                }
              ]
            }

            Block types:
            - "paragraph": Has "lines" array. Each line has "id", "text", and optional "highlight".
            - "formula": Has "formula" string (LaTeX/plain math notation).
            - "diagram": Has "diagramType" ("mermaid") and "content" (Mermaid syntax).
              * Use flowchart TD (not graph TD) for diagrams. Quote labels: A["Text here"].

            Highlight types for lines: "important", "definition", "warning", "exam", "focus", "note".

            IMPORTANT:
            - Every block must have a unique "id" (e.g. "block-1", "block-2").
            - Every line must have a unique "id" (e.g. "l1", "l2").
            - Use "write_to_board" for NEW content. Use "update_board_line" / "highlight_board_line" for edits to existing content.

    Returns:
        Confirmation with block count and board summary.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        doc = json.loads(board_json) if isinstance(board_json, str) else board_json

        # Ensure required fields
        if "id" not in doc:
            doc["id"] = "board-1"
        if "version" not in doc:
            doc["version"] = 1

        # Apply as setBoard operation on backend state
        current = _get_board(context)
        op = {"type": "setBoard", "document": doc}
        new_doc = apply_operation(current, op)
        _set_board(context, new_doc)

        # Send full board to frontend
        await send_rpc("set_board", json.dumps(doc), frontend_id=frontend_id)

        block_count = len(doc.get("blocks", []))
        summary = board_to_summary(new_doc)
        return f"Board updated with {block_count} blocks.\n{summary}"

    except Exception as e:
        logger.error(f"write_to_board failed: {e}")
        return f"Failed to update board: {str(e)}"


@function_tool()
async def update_board_line(
    context: RunContext,
    block_id: str,
    line_id: str,
    new_text: str,
) -> str:
    """Update a specific line of text on the board.

    Use this to edit an existing line without replacing the entire board.

    Args:
        block_id: The ID of the block containing the line (e.g. "block-1").
        line_id: The ID of the line to update (e.g. "l2").
        new_text: The new text for the line.

    Returns:
        Confirmation string.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        op = {"type": "updateLine", "blockId": block_id, "lineId": line_id, "newText": new_text}
        current = _get_board(context)
        new_doc = apply_operation(current, op)

        if new_doc["version"] == current["version"]:
            return f"Line {line_id} in block {block_id} not found."

        _set_board(context, new_doc)
        await _send_board_op(op, frontend_id)
        return f"Updated line {line_id} in block {block_id}."

    except Exception as e:
        logger.error(f"update_board_line failed: {e}")
        return f"Failed to update line: {str(e)}"


@function_tool()
async def add_board_block(
    context: RunContext,
    block_json: str,
    after_block_id: str = "",
) -> str:
    """Add a new block to the board.

    Args:
        block_json: JSON string of the block to add. Examples:
            Paragraph: {"id": "block-4", "type": "paragraph", "lines": [{"id": "l1", "text": "New paragraph."}]}
            Formula: {"id": "block-5", "type": "formula", "formula": "a^2 + b^2 = c^2"}
            Diagram: {"id": "block-6", "type": "diagram", "diagramType": "mermaid", "content": "flowchart TD\\n  A --> B"}
        after_block_id: Optional. Insert after this block ID. If empty, appends to the end.

    Returns:
        Confirmation string.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        block = json.loads(block_json) if isinstance(block_json, str) else block_json

        op: dict = {"type": "addBlock", "block": block}
        if after_block_id:
            op["afterBlockId"] = after_block_id

        current = _get_board(context)
        new_doc = apply_operation(current, op)
        _set_board(context, new_doc)

        await _send_board_op(op, frontend_id)
        return f"Added block {block.get('id', '?')} ({block.get('type', '?')})."

    except Exception as e:
        logger.error(f"add_board_block failed: {e}")
        return f"Failed to add block: {str(e)}"


@function_tool()
async def highlight_board_line(
    context: RunContext,
    block_id: str,
    line_id: str,
    highlight_type: str,
) -> str:
    """Highlight a specific line on the board.

    Args:
        block_id: The ID of the block containing the line (e.g. "block-1").
        line_id: The ID of the line to highlight (e.g. "l2").
        highlight_type: One of: "important", "definition", "warning", "exam", "focus", "note".

    Returns:
        Confirmation string.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        op = {"type": "highlightLine", "blockId": block_id, "lineId": line_id, "highlightType": highlight_type}
        current = _get_board(context)
        new_doc = apply_operation(current, op)

        if new_doc["version"] == current["version"]:
            return f"Line {line_id} in block {block_id} not found."

        _set_board(context, new_doc)
        await _send_board_op(op, frontend_id)
        return f"Highlighted line {line_id} as '{highlight_type}'."

    except Exception as e:
        logger.error(f"highlight_board_line failed: {e}")
        return f"Failed to highlight line: {str(e)}"


@function_tool()
async def insert_board_line(
    context: RunContext,
    block_id: str,
    after_line_id: str,
    line_json: str,
) -> str:
    """Insert a new line after a specific line in a paragraph block.

    Args:
        block_id: The ID of the paragraph block (e.g. "block-1").
        after_line_id: Insert after this line ID (e.g. "l2").
        line_json: JSON string of the new line: {"id": "l2b", "text": "New line text."}

    Returns:
        Confirmation string.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        new_line = json.loads(line_json) if isinstance(line_json, str) else line_json

        op = {"type": "insertLineAfter", "blockId": block_id, "afterLineId": after_line_id, "newLine": new_line}
        current = _get_board(context)
        new_doc = apply_operation(current, op)

        if new_doc["version"] == current["version"]:
            return f"Line {after_line_id} in block {block_id} not found."

        _set_board(context, new_doc)
        await _send_board_op(op, frontend_id)
        return f"Inserted line {new_line.get('id', '?')} after {after_line_id}."

    except Exception as e:
        logger.error(f"insert_board_line failed: {e}")
        return f"Failed to insert line: {str(e)}"


@function_tool()
async def delete_board_line(
    context: RunContext,
    block_id: str,
    line_id: str,
) -> str:
    """Delete a specific line from a paragraph block.

    Args:
        block_id: The ID of the block containing the line (e.g. "block-1").
        line_id: The ID of the line to delete (e.g. "l2").

    Returns:
        Confirmation string.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        op = {"type": "deleteLine", "blockId": block_id, "lineId": line_id}
        current = _get_board(context)
        new_doc = apply_operation(current, op)

        if new_doc["version"] == current["version"]:
            return f"Line {line_id} in block {block_id} not found."

        _set_board(context, new_doc)
        await _send_board_op(op, frontend_id)
        return f"Deleted line {line_id} from block {block_id}."

    except Exception as e:
        logger.error(f"delete_board_line failed: {e}")
        return f"Failed to delete line: {str(e)}"


@function_tool()
async def clear_board_content(
    context: RunContext,
) -> str:
    """Clear all content from the structured board and reset it to empty.

    Use this when the user asks to clear, reset, wipe, or start fresh on the board.

    Returns:
        Confirmation string.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        empty_doc = create_empty_board()
        _set_board(context, empty_doc)
        await send_rpc("clear_board", {}, frontend_id=frontend_id)
        return "Cleared the board."

    except Exception as e:
        logger.error(f"clear_board_content failed: {e}")
        return f"Failed to clear board: {str(e)}"
