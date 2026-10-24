"""Render the public game screen: board (incl. the 2 spawn rows), ghost outline, HOLD, one NEXT piece, score/lines/level.

This is the complete observation. No column or row labels are drawn; the actor reads the raw picture."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine import CELLS, HIDDEN, H, KINDS, W

PREVIEW = 1  # classic one-piece preview
CELL = 18
BX, BY = 10, 20  # board origin (top of the spawn rows)
PANEL_X = BX + W * CELL + 10
IMG_W, IMG_H = PANEL_X + 100, BY + H * CELL + 20
COLORS = {"I": (0, 240, 240), "J": (40, 80, 240), "L": (240, 160, 0), "O": (240, 240, 0),
          "S": (0, 220, 0), "T": (170, 0, 240), "Z": (240, 0, 0)}
BG, GRID, TEXT = (12, 12, 20), (36, 36, 52), (230, 230, 240)
SPAWN_BG, SPAWN_LINE = (30, 14, 20), (200, 90, 90)
_FONT = ImageFont.load_default()
NEXT_BOX = (PANEL_X, BY + 60, PANEL_X + 60, BY + 110)  # pixel box of the NEXT preview (public screen region)
SPAWN_STRIP = (BX, BY, BX + W * CELL, BY + HIDDEN * CELL)  # pixel box of the spawn rows (public screen region)


def _cell(d: ImageDraw.ImageDraw, x: int, y: int, color, size: int = CELL):
    d.rectangle([x, y, x + size - 1, y + size - 1], fill=color)
    d.rectangle([x, y, x + size - 1, y + size - 1], outline=tuple(int(c * 0.55) for c in color))


def _mini(d, kind: str, x: int, y: int, size: int = 12):
    rows = [r for r, _ in CELLS[kind][0]]
    cols = [c for _, c in CELLS[kind][0]]
    ox = x + (4 - (max(cols) - min(cols) + 1)) * size // 2
    for r, c in CELLS[kind][0]:
        _cell(d, ox + (c - min(cols)) * size, y + (r - min(rows)) * size, COLORS[kind], size)


def render(env, ghost: bool = True) -> np.ndarray:
    img = Image.new("RGB", (IMG_W, IMG_H), BG)
    d = ImageDraw.Draw(img)
    for r in range(H):
        for c in range(W):
            x, y = BX + c * CELL, BY + r * CELL
            v = env.board[r, c]
            if v:
                _cell(d, x, y, COLORS[KINDS[v - 1]])
            elif r < HIDDEN:
                d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=SPAWN_BG)
            else:
                d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=GRID)
    d.rectangle([BX - 1, BY - 1, BX + W * CELL, BY + H * CELL], outline=(120, 120, 150))
    d.line([BX, BY + HIDDEN * CELL, BX + W * CELL - 1, BY + HIDDEN * CELL], fill=SPAWN_LINE)
    if not env.over:
        if ghost:
            for r, c in env.cells(y=env.drop_y()):
                x, y = BX + c * CELL, BY + r * CELL
                d.rectangle([x + 1, y + 1, x + CELL - 2, y + CELL - 2], outline=COLORS[env.kind])
        for r, c in env.cells():
            _cell(d, BX + c * CELL, BY + r * CELL, COLORS[env.kind])
    d.text((PANEL_X, BY - 14), "HOLD", fill=TEXT, font=_FONT)
    if env.hold:
        _mini(d, env.hold, PANEL_X, BY + 4)
    d.text((PANEL_X, BY + 50), "NEXT", fill=TEXT, font=_FONT)
    for i, k in enumerate(env.upcoming(PREVIEW)):
        _mini(d, k, PANEL_X, BY + 66 + i * 36)
    base = BY + H * CELL - 70
    for i, (label, val) in enumerate((("SCORE", env.score), ("LINES", env.lines), ("LEVEL", env.level))):
        d.text((PANEL_X, base + i * 22), label, fill=(150, 150, 175), font=_FONT)
        d.text((PANEL_X, base + 10 + i * 22), str(val), fill=TEXT, font=_FONT)
    if env.over:
        d.rectangle([BX, BY + 170, BX + W * CELL, BY + 210], fill=(0, 0, 0))
        d.text((BX + 48, BY + 185), "GAME OVER", fill=(255, 80, 80), font=_FONT)
    return np.asarray(img)
