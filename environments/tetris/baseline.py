"""Rules baseline for the evaluator side only: it reads the true board, which no actor ever sees.

The placement rule is the El-Tetris linear heuristic over all legal (rotation, column) drops of the piece in play.
It is used as a comparison condition under identical delay, executor and clip settings, never as a policy input.
"""
from __future__ import annotations

import json

import numpy as np

from engine import CELLS, H, HIDDEN, W

WEIGHTS = {"height": -0.510066, "lines": 0.760666, "holes": -0.35663, "bump": -0.184483}


def features(board: np.ndarray) -> tuple[int, int, int, int]:
    """(aggregate height, complete lines, holes, bumpiness) of a board array (rows top to bottom)."""
    filled = board != 0
    heights = [int(H - filled[:, c].argmax()) if filled[:, c].any() else 0 for c in range(W)]
    lines = int(filled.all(axis=1).sum())
    holes = sum(int((~filled[H - h:, c]).sum()) for c, h in enumerate(heights))
    bump = sum(abs(heights[c] - heights[c + 1]) for c in range(W - 1))
    return sum(heights), lines, holes, bump


def landing(board: np.ndarray, kind: str, rot: int, col: int):
    """Cells where ``kind`` lands when dropped straight down with its left edge at ``col``; None if impossible."""
    cells = CELLS[kind][rot % 4]
    c0 = min(c for _, c in cells)
    offs = [(r, c - c0 + col) for r, c in cells]
    if any(c < 0 or c >= W for _, c in offs):
        return None
    y = 0
    if any(board[r, c] for r, c in offs):
        return None
    while all(r + y + 1 < H and not board[r + y + 1, c] for r, c in offs):
        y += 1
    out = [(r + y, c) for r, c in offs]
    return None if all(r < HIDDEN for r, _ in out) else out


def apply(board: np.ndarray, kind: str, cells) -> np.ndarray:
    board = board.copy()
    for r, c in cells:
        board[r, c] = "IJLOSTZ".index(kind) + 1
    keep = [i for i in range(H) if not (board[i] != 0).all()]
    out = np.zeros_like(board)
    if keep:
        out[H - len(keep):] = board[keep]
    return out


def choose(board: np.ndarray, kind: str):
    """Best (rot, col) by the linear heuristic, or None when nothing fits."""
    best = None
    for rot in range(4):
        for col in range(W):
            cells = landing(board, kind, rot, col)
            if cells is None:
                continue
            h, lines, holes, bump = features(apply(board, kind, cells))
            value = WEIGHTS["height"] * h + WEIGHTS["lines"] * lines + WEIGHTS["holes"] * holes + WEIGHTS["bump"] * bump
            if best is None or value > best[0]:
                best = (value, rot, col)
    return None if best is None else (best[1], best[2])


class RulesActor:
    """Evaluator-side baseline with the same request/answer interface; it is handed the true engine, not pixels."""

    def __init__(self, *, output=None, **_):
        self.counter = 0

    def act_on_truth(self, env):
        pick = choose(env.board, env.kind)
        rot, col = pick if pick else (0, 3)
        self.counter += 1
        return json.dumps({"rot": rot, "col": col, "reason": "rules baseline (true board)"}), {"wall_seconds": 0.0, "auth": "rules"}

    def close(self):
        pass
