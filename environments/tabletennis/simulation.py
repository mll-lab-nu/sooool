"""Private empirical delay scheduler; no future timing enters actor prompts."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random


def load_profile(path):
    path = Path(path)
    raw = path.read_bytes()
    profile = json.loads(raw)
    delays = profile.get("delays_s", [])
    if not delays or any(isinstance(x, bool) or not isinstance(x, (int, float)) or
                         not math.isfinite(x) or x <= 0 for x in delays):
        raise ValueError("Profile needs finite positive API delays_s")
    if profile.get("model") != "gpt-6.1-sol" or profile.get("service_tier") != "ultrafast":
        raise ValueError("Expected retained Sol/ultrafast API timing")
    terminal = profile.get("all_wire_completed_request_s", delays)
    if len(terminal) != len(delays) or any(isinstance(t, bool) or not isinstance(t, (int, float)) or
                                         not math.isfinite(t) or t < a for a, t in zip(delays, terminal)):
        raise ValueError("Terminal samples must be paired and no earlier than action readiness")
    return {**profile, "sha256": hashlib.sha256(raw).hexdigest()}


class DelayScheduler:
    def __init__(self, profile, seed, slowdown, stride):
        self.rng = random.Random(seed)
        self.delays = tuple(profile["delays_s"])
        self.terminals = tuple(profile.get("all_wire_completed_request_s", self.delays))
        self.slowdown = slowdown
        self.stride = stride

    def schedule(self, frame):
        index = self.rng.randrange(len(self.delays))
        delay = self.delays[index]
        terminal = self.terminals[index]
        # Delivery is quantized upwards to a public-camera/control boundary.
        due = math.ceil((frame + delay * 100 / self.slowdown) / self.stride) * self.stride
        terminal_frame = math.ceil((frame + terminal * 100 / self.slowdown) / self.stride) * self.stride
        return {"sampled_api_seconds": delay, "sampled_terminal_seconds": terminal,
                "delivery_frame": due, "terminal_frame": terminal_frame}

    @staticmethod
    def due(metadata, frame):
        return frame >= metadata["delivery_frame"]
