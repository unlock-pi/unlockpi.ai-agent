"""
Board Engine — applies operations to a BoardDocument (server-side source of truth).

Pure functions, no I/O. Mirrors the frontend board-engine.ts logic.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger("agent-UnlockPi")


# ── Factory ───────────────────────────────────────────────────────────

def create_empty_board() -> dict:
    """Return a fresh empty BoardDocument."""
    return {"id": "board-1", "version": 0, "blocks": []}


# ── Main Dispatcher ───────────────────────────────────────────────────

def apply_operation(doc: dict, op: dict) -> dict:
    """Apply a BoardOperation to a BoardDocument.  Returns a new dict (shallow-ish copy)."""
    op_type = op.get("type")
    if op_type == "updateLine":
        return _apply_update_line(doc, op["blockId"], op["lineId"], op["newText"])
    elif op_type == "insertLineAfter":
        return _apply_insert_line_after(doc, op["blockId"], op["afterLineId"], op["newLine"])
    elif op_type == "deleteLine":
        return _apply_delete_line(doc, op["blockId"], op["lineId"])
    elif op_type == "addBlock":
        return _apply_add_block(doc, op["block"], op.get("afterBlockId"))
    elif op_type == "deleteBlock":
        return _apply_delete_block(doc, op["blockId"])
    elif op_type == "highlightLine":
        return _apply_highlight_line(doc, op["blockId"], op["lineId"], op["highlightType"])
    elif op_type == "setBoard":
        new_doc = copy.deepcopy(op["document"])
        new_doc["version"] = doc["version"] + 1
        return new_doc
    else:
        logger.warning(f"Unknown board operation type: {op_type}")
        return doc


# ── Helpers ───────────────────────────────────────────────────────────

def _find_block_index(blocks: list[dict], block_id: str) -> int:
    for i, b in enumerate(blocks):
        if b.get("id") == block_id:
            return i
    return -1


def _find_line_index(lines: list[dict], line_id: str) -> int:
    for i, line in enumerate(lines):
        if line.get("id") == line_id:
            return i
    return -1


def _bump(doc: dict, new_blocks: list[dict]) -> dict:
    return {**doc, "version": doc["version"] + 1, "blocks": new_blocks}


# ── Operation Implementations ─────────────────────────────────────────

def _apply_update_line(doc: dict, block_id: str, line_id: str, new_text: str) -> dict:
    blocks = copy.deepcopy(doc["blocks"])
    bi = _find_block_index(blocks, block_id)
    if bi == -1 or blocks[bi].get("type") != "paragraph":
        return doc
    li = _find_line_index(blocks[bi]["lines"], line_id)
    if li == -1:
        return doc
    blocks[bi]["lines"][li]["text"] = new_text
    return _bump(doc, blocks)


def _apply_insert_line_after(doc: dict, block_id: str, after_line_id: str, new_line: dict) -> dict:
    blocks = copy.deepcopy(doc["blocks"])
    bi = _find_block_index(blocks, block_id)
    if bi == -1 or blocks[bi].get("type") != "paragraph":
        return doc
    li = _find_line_index(blocks[bi]["lines"], after_line_id)
    if li == -1:
        return doc
    blocks[bi]["lines"].insert(li + 1, new_line)
    return _bump(doc, blocks)


def _apply_delete_line(doc: dict, block_id: str, line_id: str) -> dict:
    blocks = copy.deepcopy(doc["blocks"])
    bi = _find_block_index(blocks, block_id)
    if bi == -1 or blocks[bi].get("type") != "paragraph":
        return doc
    li = _find_line_index(blocks[bi]["lines"], line_id)
    if li == -1:
        return doc
    blocks[bi]["lines"].pop(li)
    return _bump(doc, blocks)


def _apply_add_block(doc: dict, block: dict, after_block_id: str | None = None) -> dict:
    blocks = copy.deepcopy(doc["blocks"])
    block = copy.deepcopy(block)
    if after_block_id:
        bi = _find_block_index(blocks, after_block_id)
        if bi == -1:
            blocks.append(block)
        else:
            blocks.insert(bi + 1, block)
    else:
        blocks.append(block)
    return _bump(doc, blocks)


def _apply_delete_block(doc: dict, block_id: str) -> dict:
    blocks = copy.deepcopy(doc["blocks"])
    bi = _find_block_index(blocks, block_id)
    if bi == -1:
        return doc
    blocks.pop(bi)
    return _bump(doc, blocks)


def _apply_highlight_line(doc: dict, block_id: str, line_id: str, highlight_type: str) -> dict:
    blocks = copy.deepcopy(doc["blocks"])
    bi = _find_block_index(blocks, block_id)
    if bi == -1 or blocks[bi].get("type") != "paragraph":
        return doc
    li = _find_line_index(blocks[bi]["lines"], line_id)
    if li == -1:
        return doc
    blocks[bi]["lines"][li]["highlight"] = highlight_type
    return _bump(doc, blocks)


# ── Summary Generation (for LLM context) ─────────────────────────────

def board_to_summary(doc: dict) -> str:
    """Generate a compact text summary of the board for LLM context injection.

    Example output:
        Block1 (paragraph): Photosynthesis explanation (3 lines)
        Block2 (formula): 6CO2 + 6H2O → C6H12O6 + 6O2
        Block3 (diagram/mermaid): Energy flow diagram
    """
    if not doc or not doc.get("blocks"):
        return "Board is empty."

    parts: list[str] = []
    for i, block in enumerate(doc["blocks"], 1):
        btype = block.get("type", "unknown")
        if btype == "paragraph":
            lines = block.get("lines", [])
            first_line = lines[0]["text"][:60] if lines else ""
            suffix = f" ({len(lines)} lines)" if len(lines) > 1 else ""
            parts.append(f"Block{i} (paragraph): {first_line}{suffix}")
        elif btype == "formula":
            parts.append(f"Block{i} (formula): {block.get('formula', '')[:80]}")
        elif btype == "diagram":
            dtype = block.get("diagramType", "")
            content_preview = block.get("content", "")[:50].replace("\n", " ")
            parts.append(f"Block{i} (diagram/{dtype}): {content_preview}")
        else:
            parts.append(f"Block{i} ({btype})")
    return "\n".join(parts)
