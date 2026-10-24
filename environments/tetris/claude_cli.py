"""Stateless Claude Code CLI transport: one fresh process per request, no tools, no session, no skills, no settings.

This adapter is a separate provider condition from the repository's ChatGPT subscription transport. Each call sends
the system text, the task text and the screenshot(s) to ``claude -p`` and returns the public answer text with the
CLI's reported timing and token usage. Thinking is whatever the CLI reports at the requested effort; it is not
archived. Credentials are the CLI's own sign-in; nothing is read from files.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

EFFORTS = ("low", "medium", "high")


class ClaudeCliClient:
    def __init__(self, *, output, system, model="opus", effort="low", timeout=240.0):
        if effort not in EFFORTS:
            raise ValueError("Unsupported effort")
        self.executable = os.environ.get("SOL_CLAUDE_BIN") or shutil.which("claude")
        if not self.executable:
            raise RuntimeError("Install Claude Code CLI and sign in first; the claude provider has no fallback.")
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.system, self.model, self.effort, self.timeout = system, model, effort, float(timeout)
        self.counter = 0
        try:
            version = subprocess.run([self.executable, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            version = None
        self.transport = {"adapter": "claude code cli, stateless -p", "model_alias": model, "effort": effort,
                          "cli_version": version, "resolved_models": {}, "tools": "none", "session_persistence": False}
        self._write_transport()

    def _write_transport(self):
        (self.output / "transport.json").write_text(json.dumps(self.transport, indent=2))

    def act(self, prompt, images, directory=None):
        directory = Path(directory or self.output / f"call-{self.counter:05d}")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "prompt.txt").write_text(prompt)
        content = []
        for i, data in enumerate(images):
            (directory / f"image_{i}.png").write_bytes(data)
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                        "data": base64.b64encode(data).decode()}})
        content.append({"type": "text", "text": prompt})
        message = json.dumps({"type": "user", "message": {"role": "user", "content": content}})
        command = [self.executable, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
                   "--model", self.model, "--effort", self.effort, "--tools", "", "--system-prompt", self.system,
                   "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config", "--setting-sources", ""]
        env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY",)}
        started = time.monotonic()
        process = subprocess.run(command, input=message, capture_output=True, text=True, timeout=self.timeout, env=env)
        wall = time.monotonic() - started
        rows = []
        for line in process.stdout.splitlines():
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        result = [r for r in rows if r.get("type") == "result"]
        if process.returncode != 0 or not result or result[-1].get("is_error"):
            (directory / "error.txt").write_text(process.stdout[-4000:] + "\n" + process.stderr[-4000:])
            raise RuntimeError("Claude CLI call failed; see " + str(directory / "error.txt"))
        final = result[-1]
        usage = final.get("usage") or {}
        answer = final.get("result") or ""
        resolved = sorted((final.get("modelUsage") or {}).keys()) or [m for r in rows if r.get("type") == "assistant"
                                                                      for m in [(r.get("message") or {}).get("model")] if m]
        for name in resolved:  # the exact model id the CLI resolved the alias to, kept per run
            self.transport["resolved_models"][name] = self.transport["resolved_models"].get(name, 0) + 1
        self._write_transport()
        meta = {"wall_seconds": wall, "api_ms": final.get("duration_api_ms"), "turns": final.get("num_turns"),
                "output_tokens": usage.get("output_tokens"),
                "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
                "model": self.model, "resolved_model": resolved[0] if len(resolved) == 1 else resolved or None,
                "effort": self.effort, "auth": "claude-cli"}
        (directory / "result.json").write_text(json.dumps({"answer": answer, "meta": meta}, indent=2))
        self.counter += 1
        return answer, meta

    def close(self):
        pass
