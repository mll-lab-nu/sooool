"""Single-player Tetris engine: 60 Hz logic, deterministic per seed.

Rules: 10x20 visible (+2 hidden rows), 7-bag, SRS rotation and kicks, one hold,
DAS/ARR on held left/right, lock delay with a reset cap, guideline scoring.

Action (held-button) semantics, one value per 60 Hz frame:
    0 noop   1 left   2 right   3 rotate cw   4 rotate ccw   5 soft drop   6 hard drop   7 hold
left/right repeat via DAS/ARR while held; rotate, hard drop and hold fire only on the
frame the action CHANGES (a press edge); soft drop moves one row every 2 frames while held.
"""
from __future__ import annotations

import random
from collections import deque

import numpy as np

W, H, HIDDEN = 10, 22, 2
KINDS = "IJLOSTZ"  # piece ids on the board are 1..7 in this order
SPAWN_X = {kind: (4 if kind == "O" else 3) for kind in KINDS}  # published spawn column (left edge of the bounding box)
NOOP, LEFT, RIGHT, CW, CCW, SOFT, HARD, HOLD = range(8)

_BASE = {
    "I": [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    "J": [[1, 0, 0], [1, 1, 1], [0, 0, 0]],
    "L": [[0, 0, 1], [1, 1, 1], [0, 0, 0]],
    "O": [[1, 1], [1, 1]],
    "S": [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
    "T": [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
    "Z": [[1, 1, 0], [0, 1, 1], [0, 0, 0]],
}
# CELLS[kind][rot] = list of (row, col) inside the piece box
CELLS = {}
for _k, _m in _BASE.items():
    _a, _rots = np.array(_m), []
    for _ in range(4):
        _rots.append([(int(r), int(c)) for r, c in zip(*np.nonzero(_a))])
        _a = np.rot90(_a, -1)
    CELLS[_k] = _rots

# SRS kick tables, (dx, dy) with y UP as in the guideline; converted to board rows when applied.
_JLSTZ = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)], (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)], (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)], (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)], (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
}
_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)], (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)], (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)], (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)], (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
}
LINE_SCORE = [0, 100, 300, 500, 800]


class Tetris:
    def __init__(self, seed: int = 0, start_level: int = 1, das: int = 10, arr: int = 2,
                 lock_delay: int = 30, max_lock_resets: int = 15, next_count: int = 5):
        self.das, self.arr = das, arr
        self.lock_delay, self.max_lock_resets, self.next_count = lock_delay, max_lock_resets, next_count
        self.start_level = start_level
        self.reset(seed)

    # ---- lifecycle -------------------------------------------------------------------
    def reset(self, seed: int | None = None):
        if seed is not None:
            self.seed = seed
        self.rng = random.Random(self.seed)
        self.board = np.zeros((H, W), dtype=np.int8)
        self.queue: deque[str] = deque()
        self.hold: str | None = None
        self.hold_used = False
        self.score = self.lines = self.tick = self.pieces = 0
        self.level = self.start_level
        self.over = False
        self.prev_action = NOOP
        self.das_timer = self.soft_acc = 0
        self.grav_acc = 0.0
        self.last_clear = 0
        self._spawn(self._pop())
        return self

    def _refill(self):
        while len(self.queue) < self.next_count + 7:
            bag = list(KINDS)
            self.rng.shuffle(bag)
            self.queue.extend(bag)

    def _pop(self) -> str:
        self._refill()
        return self.queue.popleft()

    def upcoming(self, n: int | None = None) -> list[str]:
        self._refill()
        return list(self.queue)[: (self.next_count if n is None else n)]

    # ---- geometry --------------------------------------------------------------------
    def _spawn(self, kind: str):
        self.kind, self.rot = kind, 0
        self.x, self.y = SPAWN_X[kind], 0
        self.ground_timer = self.lock_resets = 0
        self.grav_acc = 0.0
        if self._collides(self.kind, self.rot, self.x, self.y):
            self.over = True

    def cells(self, kind=None, rot=None, x=None, y=None):
        kind = self.kind if kind is None else kind
        rot = self.rot if rot is None else rot
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(y + r, x + c) for r, c in CELLS[kind][rot]]

    def _collides(self, kind, rot, x, y) -> bool:
        for r, c in self.cells(kind, rot, x, y):
            if c < 0 or c >= W or r >= H or (r >= 0 and self.board[r, c]):
                return True
        return False

    def _grounded(self) -> bool:
        return self._collides(self.kind, self.rot, self.x, self.y + 1)

    def drop_y(self, kind=None, rot=None, x=None, y=None) -> int:
        kind = self.kind if kind is None else kind
        rot = self.rot if rot is None else rot
        x = self.x if x is None else x
        y = self.y if y is None else y
        while not self._collides(kind, rot, x, y + 1):
            y += 1
        return y

    # ---- moves -----------------------------------------------------------------------
    def _after_successful_move(self):
        if self._grounded() and self.lock_resets < self.max_lock_resets:
            self.ground_timer = 0
            self.lock_resets += 1

    def _shift(self, dx: int) -> bool:
        if self._collides(self.kind, self.rot, self.x + dx, self.y):
            return False
        self.x += dx
        self._after_successful_move()
        return True

    def _rotate(self, d: int) -> bool:
        if self.kind == "O":
            return False
        new = (self.rot + d) % 4
        table = _I if self.kind == "I" else _JLSTZ
        for dx, dy in table[(self.rot, new)]:
            if not self._collides(self.kind, new, self.x + dx, self.y - dy):
                self.x, self.y, self.rot = self.x + dx, self.y - dy, new
                self._after_successful_move()
                return True
        return False

    def _down(self) -> bool:
        if self._collides(self.kind, self.rot, self.x, self.y + 1):
            return False
        self.y += 1
        self.ground_timer = self.lock_resets = 0
        return True

    def _hold(self):
        if self.hold_used:
            return
        cur = self.kind
        if self.hold is None:
            self._spawn(self._pop())
        else:
            self._spawn(self.hold)
        self.hold, self.hold_used = cur, True

    def _lock(self) -> int:
        cells = self.cells()
        for r, c in cells:
            if r >= 0:
                self.board[r, c] = KINDS.index(self.kind) + 1
        lockout = all(r < HIDDEN for r, _ in cells)
        full = [r for r in range(H) if self.board[r].all()]
        n = len(full)
        if n:
            keep = self.board[[r for r in range(H) if r not in full]]
            self.board = np.vstack([np.zeros((n, W), dtype=np.int8), keep])
            self.lines += n
            self.score += LINE_SCORE[n] * self.level
            self.level = self.start_level + self.lines // 10
        self.last_clear = n
        self.pieces += 1
        self.hold_used = False
        if lockout:
            self.over = True
        else:
            self._spawn(self._pop())
        return n

    # ---- stepping --------------------------------------------------------------------
    def step(self, action: int = NOOP):
        """Advance one 60 Hz frame. Returns (score_delta, terminated, info)."""
        if self.over:
            return 0, True, self.info()
        before, edge = self.score, action != self.prev_action
        locked = False
        if action in (LEFT, RIGHT):
            d = -1 if action == LEFT else 1
            if edge:
                self.das_timer = 0
                self._shift(d)
            else:
                self.das_timer += 1
                if self.das_timer >= self.das and (self.das_timer - self.das) % self.arr == 0:
                    self._shift(d)
        else:
            self.das_timer = 0
        if edge and action == CW:
            self._rotate(1)
        elif edge and action == CCW:
            self._rotate(-1)
        elif edge and action == HOLD:
            self._hold()
        elif edge and action == HARD:
            gain = self.drop_y() - self.y
            self.y += gain
            self.score += 2 * gain
            locked = True
        if action == SOFT:
            self.soft_acc += 1
            if self.soft_acc >= 2:
                self.soft_acc = 0
                if self._down():
                    self.score += 1
        else:
            self.soft_acc = 0
        if not locked and not self.over:
            self.grav_acc += 1.0 / self.frames_per_row()
            while self.grav_acc >= 1.0:
                self.grav_acc -= 1.0
                self._down()
            if self._grounded():
                self.ground_timer += 1
                if self.ground_timer >= self.lock_delay:
                    locked = True
        if locked:
            self._lock()
        self.prev_action = action
        self.tick += 1
        return self.score - before, self.over, self.info()

    def frames_per_row(self) -> float:
        return max(1.0 / 20, 60 * (0.8 - (self.level - 1) * 0.007) ** (self.level - 1))

    def info(self) -> dict:
        return {"score": self.score, "lines": self.lines, "level": self.level, "tick": self.tick,
                "pieces": self.pieces, "over": self.over}
