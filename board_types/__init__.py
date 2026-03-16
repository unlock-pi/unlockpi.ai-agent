"""
Board data model — structured document types for the classroom board.

Mirrors the frontend TypeScript types in src/types/board.ts.
The board is a document tree: BoardDocument → Block[] → Line[].
"""

from typing import Any, Literal, Optional, TypedDict


# ── Line ──────────────────────────────────────────────────────────────

HighlightType = Literal["important", "definition", "warning", "exam", "focus", "note"]


class Line(TypedDict, total=False):
    id: str
    text: str
    highlight: HighlightType


# ── Blocks ────────────────────────────────────────────────────────────

class ParagraphBlock(TypedDict):
    id: str
    type: Literal["paragraph"]
    lines: list[Line]


class FormulaBlock(TypedDict):
    id: str
    type: Literal["formula"]
    formula: str


class DiagramBlock(TypedDict):
    id: str
    type: Literal["diagram"]
    diagramType: Literal["mermaid"]
    content: str


Block = ParagraphBlock | FormulaBlock | DiagramBlock


# ── Board Document ────────────────────────────────────────────────────

class BoardDocument(TypedDict):
    id: str
    version: int
    blocks: list[Block]


# ── Operations ────────────────────────────────────────────────────────

class UpdateLineOp(TypedDict):
    type: Literal["updateLine"]
    blockId: str
    lineId: str
    newText: str


class InsertLineAfterOp(TypedDict):
    type: Literal["insertLineAfter"]
    blockId: str
    afterLineId: str
    newLine: Line


class DeleteLineOp(TypedDict):
    type: Literal["deleteLine"]
    blockId: str
    lineId: str


class AddBlockOp(TypedDict, total=False):
    type: Literal["addBlock"]
    block: Block
    afterBlockId: str


class DeleteBlockOp(TypedDict):
    type: Literal["deleteBlock"]
    blockId: str


class HighlightLineOp(TypedDict):
    type: Literal["highlightLine"]
    blockId: str
    lineId: str
    highlightType: HighlightType


class SetBoardOp(TypedDict):
    type: Literal["setBoard"]
    document: BoardDocument


BoardOperation = (
    UpdateLineOp
    | InsertLineAfterOp
    | DeleteLineOp
    | AddBlockOp
    | DeleteBlockOp
    | HighlightLineOp
    | SetBoardOp
)
