"""Profile frozen public task inputs against a loopback Chat Completions server.

This is inference measurement, not gameplay evaluation. No provider fallback.
Corpus files contain only model-visible prompts/images and validator metadata.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def validate(text, case, terminal=False):
    """Return the task's canonical action; do not execute or repair it."""
    game = case["game"]
    if game == "racing":
        from environments.racing.lane import parse_lane
        return parse_lane(text)
    if game == "rhythm":
        from environments.rhythm.experiments.rhythm.model_compact_policy import parse
        from environments.rhythm.experiments.rhythm.model_commentary import action_prefix, complete
        if case.get("commentary"):
            action, _ = complete(text) if terminal else action_prefix(text)
            return parse(action)
        return parse(text)
    if game == "asterix" and case.get("output_format") == "action":
        if text.strip() not in list("012345678"):
            raise ValueError("Expected one action digit 0..8")
        return int(text.strip())
    if game == "tabletennis":
        from environments.tabletennis.tactics import decode_intent
        if case.get("schema"):
            from jsonschema import validate as schema_validate
            schema_validate(json.loads(text), case["schema"])
        return decode_intent(text)
    if game == "badminton":
        from environments.badminton.api import decode_response
        return decode_response(text, case["spec"])
    if game == "touhou":
        from jsonschema import validate as schema_validate
        obj = json.loads(text)
        schema_validate(obj, case["schema"])
        return obj
    if game == "asterix":
        from jsonschema import validate as schema_validate
        from runtime.asterix_api import SCHEMA
        obj = json.loads(text)
        schema_validate(obj, SCHEMA)
        if not obj["reason"].strip():
            raise ValueError("Empty explanation")
        return obj
    if game == "roadster":
        obj = json.loads(text)
        from jsonschema import validate as schema_validate
        schema_validate(obj, case["schema"])
        buttons = obj["keys"]
        if any(a in buttons and b in buttons for a, b in
               [("ArrowLeft", "ArrowRight"), ("KeyQ", "KeyE"), ("Space", "KeyS")]):
            raise ValueError("Opposing buttons")
        return obj
    raise ValueError("Unsupported task: " + game)


def read_corpus(path):
    rows = json.loads(path.read_text())
    seen = set()
    for row in rows:
        identity = row["id"]
        if identity in seen:
            raise ValueError("Duplicate case ID")
        seen.add(identity)
        if digest(row["prompt"].encode()) != row["prompt_sha256"]:
            raise ValueError("Prompt checksum mismatch")
        for item in row["images"]:
            file = (path.parent / item["path"]).resolve()
            if not file.is_relative_to(path.parent.resolve()):
                raise ValueError("Image escapes corpus")
            if digest(file.read_bytes()) != item["sha256"]:
                raise ValueError("Image checksum mismatch")
        if not row["images"]:
            raise ValueError("Visual task has no images")
    return rows


def payload_for(case, corpus_dir):
    content = [{"type": "text", "text": case["prompt"]}]
    for item in case["images"]:
        raw = (corpus_dir / item["path"]).read_bytes()
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(raw).decode(),
            "detail": "high"}})
    messages = []
    if case.get("system"):
        messages.append({"role": "system", "content": case["system"]})
    messages.append({"role": "user", "content": content})
    return {"model": MODEL, "messages": messages, "stream": True,
            "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"thinking": False},
            "temperature": 0, "max_tokens": case.get("max_tokens", 512)}


def consume(lines, case, started, clock=time.perf_counter, event_log=None):
    record = {"text": "", "ttft_s": None, "action_ready_s": None,
              "finish_s": None, "stream_done_s": None, "usage": None,
              "models": [], "finish_reason": None, "valid": False}
    ready = None
    try:
        for raw in lines:
            if not raw.startswith(b"data:"):
                continue
            data = raw[5:].strip()
            now = clock() - started
            if now > 120:
                raise TimeoutError("Total inference deadline exceeded")
            if data == b"[DONE]":
                record["stream_done_s"] = now
                break
            event = json.loads(data)
            if any(c.get("delta", {}).get("reasoning_content") for c in event.get("choices", [])):
                raise ValueError("Server ignored thinking-disabled configuration")
            if event_log:
                event_log.write(json.dumps({"received_s": now, "event": event}) + "\n")
                event_log.flush()
            if "error" in event:
                raise ValueError("Inference server returned an error")
            model = event.get("model")
            if model and model not in record["models"]:
                record["models"].append(model)
            if event.get("usage") is not None:
                record["usage"] = event["usage"]
            for choice in event.get("choices", []):
                delta = choice.get("delta", {}).get("content") or ""
                if delta:
                    if record["ttft_s"] is None:
                        record["ttft_s"] = now
                    record["text"] += delta
                    if ready is None:
                        try:
                            candidate = validate(record["text"], case)
                        except Exception:
                            pass
                        else:
                            ready = candidate
                            record["action_ready_s"] = clock() - started
                if choice.get("finish_reason"):
                    record["finish_reason"] = choice["finish_reason"]
                    record["finish_s"] = now
        final = validate(record["text"], case, terminal=True)
        if ready is None or final != ready:
            raise ValueError("Action missing or changed after first readiness")
        if record["models"] != [MODEL]:
            raise ValueError("Unexpected or missing served model")
        if record["finish_reason"] != "stop" or record["stream_done_s"] is None:
            raise ValueError("Incomplete stream")
        if not isinstance(record["usage"], dict):
            raise ValueError("Missing terminal usage")
        record["valid"] = True
    except Exception as exc:
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)[:500]
    record["transport_complete_s"] = clock() - started
    return record


def measure(case, corpus_dir, endpoint, directory):
    directory.mkdir()
    payload = payload_for(case, corpus_dir)
    write(directory / "input.json", case)
    started = time.perf_counter()
    try:
        req = urllib.request.Request(endpoint + "/chat/completions",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as response, \
                (directory / "events.jsonl").open("w") as log:
            result = consume(response, case, started, event_log=log)
    except Exception as exc:
        result = {"valid": False, "error_type": type(exc).__name__,
                  "transport_error": True, "http_status": getattr(exc, "code", None),
                  "transport_complete_s": time.perf_counter() - started}
    result.update(case_id=case["id"], game=case["game"])
    write(directory / "result.json", result)
    return result


def summarize(rows):
    result = {"attempted": len(rows), "valid": sum(r["valid"] for r in rows),
              "latency_condition": "valid terminal-verified responses only"}
    result["failed"] = result["attempted"] - result["valid"]
    for metric in ("ttft_s", "action_ready_s", "finish_s", "stream_done_s", "transport_complete_s"):
        values = sorted(r[metric] for r in rows if r["valid"] and r.get(metric) is not None)
        if values:
            result[metric] = {"n": len(values), "p50": statistics.median(values),
                "p90": values[math.ceil(.90 * len(values))-1],
                "p99": values[math.ceil(.99 * len(values))-1], "max": values[-1],
                "samples": values}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    url = urllib.parse.urlparse(args.endpoint)
    if url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1"):
        parser.error("Only local inference endpoints are permitted; no paid API fallback")
    if args.concurrency < 1 or args.repeats < 1:
        parser.error("Positive concurrency and repeats required")
    cases = read_corpus(args.corpus)
    if args.check_only:
        print(json.dumps({"cases": len(cases), "games": sorted({c["game"] for c in cases})}))
        return
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "protocol.json", {
        "model": MODEL, "execution_mode": "local_frozen_input_profile", "gameplay": False,
        "corpus_sha256": digest(args.corpus.read_bytes()), "endpoint": args.endpoint,
        "concurrency": args.concurrency, "repeats": args.repeats, "thinking": False,
        "temperature": 0, "retries": 0, "cache": "natural; warmup excluded; repeats labeled",
        "output_constraints": "prompt only; native validation; no grammar-constrained decoding",
        "load": "closed-loop worker pool within each task; task groups sequential",
        "timing": "client HTTP submission to server stream; excludes screenshot capture and action execution",
        "percentiles": "nearest-rank p90/p99, median p50; descriptive small-sample estimates"})
    all_rows = []
    for game in sorted({c["game"] for c in cases}):
        group = [c for c in cases if c["game"] == game]
        warmup = measure(group[0], args.corpus.parent, args.endpoint, args.output / (game+"-warmup"))
        write(args.output / (game+"-warmup.json"), warmup)
        if warmup.get("transport_error"):
            raise RuntimeError("Warmup transport failed; refusing to spend the experiment on failed requests")
        # A failed action is still useful evidence; measure remaining cases too.
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            jobs = []
            for repeat in range(args.repeats):
                for index, case in enumerate(group):
                    name = f"{game}-r{repeat:02d}-{index:03d}"
                    jobs.append((repeat, pool.submit(measure, case, args.corpus.parent,
                                                    args.endpoint, args.output / name)))
            rows = []
            for repeat, job in jobs:
                row = job.result()
                row["repeat"] = repeat
                rows.append(row)
        all_rows.extend(rows)
        report = summarize(rows)
        report["by_repeat"] = {str(r): summarize([v for v in rows if v["repeat"] == r])
                               for r in range(args.repeats)}
        write(args.output / (game+"-profile.json"), report)
        print(json.dumps({"game": game, "attempted": report["attempted"], "valid": report["valid"]}), flush=True)
        write(args.output / "measurements.json", all_rows)
    write(args.output / "summary.json", {game: summarize([r for r in all_rows if r["game"] == game])
                                        for game in sorted({c["game"] for c in cases})})


if __name__ == "__main__":
    main()
