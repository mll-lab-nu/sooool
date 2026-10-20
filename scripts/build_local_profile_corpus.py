"""Pack exported, model-visible task records into an immutable portable corpus."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.local_profile import digest, read_corpus, validate, write

GAMES = {"asterix", "badminton", "racing", "rhythm", "tabletennis", "touhou", "roadster"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--records", type=Path, required=True,
                   help="Export JSON: prompt, image_paths, provenance, game, validator metadata")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-partial", action="store_true")
    a = p.parse_args()
    source = json.loads(a.records.read_text())
    games = {r["game"] for r in source}
    if not a.allow_partial and games != GAMES:
        raise ValueError(f"Missing/extra task coverage: {GAMES ^ games}")
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "images").mkdir()
    rows, seen, coverage = [], set(), {}
    for original in source:
        if original.get("image_sha256") is not None and len(original["image_sha256"]) != len(original["image_paths"]):
            raise ValueError("Source image hash count mismatch")
        row = {k: original[k] for k in (
            "game", "prompt", "system", "provenance", "schema", "spec", "commentary",
            "output_format", "max_tokens") if k in original}
        if not row.get("provenance"):
            raise ValueError("Every sample requires source provenance")
        row["prompt_sha256"] = digest(row["prompt"].encode())
        row["images"] = []
        for index, name in enumerate(original["image_paths"]):
            image = Path(name)
            if not image.is_absolute():
                image = a.records.parent / image
            raw = image.read_bytes()
            if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Expected unchanged PNG observation")
            sha = digest(raw)
            expected = original.get("image_sha256")
            if expected is not None and expected[index] != sha:
                raise ValueError("Source image hash mismatch")
            target = f"images/{sha}.png"
            (a.output / target).write_bytes(raw)
            row["images"].append({"path": target, "sha256": sha})
        identity = (row["game"], row.get("system"), row["prompt_sha256"],
                    tuple(i["sha256"] for i in row["images"]))
        if identity in seen:
            continue
        seen.add(identity)
        if original.get("reference_answer") is not None:
            validate(original["reference_answer"], row, terminal=True)
        n = coverage.get(row["game"], 0)
        row["id"] = f"{row['game']}-{n:03d}"
        coverage[row["game"]] = n + 1
        rows.append(row)
    write(a.output / "corpus.json", rows)
    read_corpus(a.output / "corpus.json")
    write(a.output / "inventory.json", {"coverage": coverage,
        "source_export_sha256": digest(a.records.read_bytes()),
        "corpus_sha256": digest((a.output / "corpus.json").read_bytes()),
        "selection": "Frozen public observations, deduplicated by system/prompt/image hashes",
        "gameplay": False, "reference_answers_sent_to_model": False})
    print(json.dumps(coverage, sort_keys=True))


if __name__ == "__main__":
    main()
