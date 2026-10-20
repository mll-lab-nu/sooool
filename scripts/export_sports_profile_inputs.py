"""Read-only export of bounded sports observations as a tar stream on stdout."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--badminton", type=Path, required=True)
    p.add_argument("--tabletennis", type=Path, required=True)
    p.add_argument("--count", type=int, default=30)
    a = p.parse_args()
    records = []
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tar:
        def add(name, raw):
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))

        for game, root in (("badminton", a.badminton), ("tabletennis", a.tabletennis)):
            pattern = "*/prompt.txt" if game == "badminton" else "*/input.json"
            files = sorted((root / "requests").glob(pattern))
            if not files:
                raise ValueError("No source observations: " + str(root))
            count = min(a.count, len(files))
            files = [files[round(i*(len(files)-1)/max(1,count-1))] for i in range(count)]
            system = (root / "source_snapshot/policies" / game /
                      ("tactical-goal-v2" if game == "badminton" else "tactical-v1") / "system.txt").read_text()
            for i, f in enumerate(files):
                if game == "badminton":
                    prompt = f.read_text()
                    snapshot, _ = json.JSONDecoder().raw_decode(prompt.split("Public snapshot:", 1)[1].lstrip())
                    extra = {"spec": snapshot["spec"], "max_tokens": 1024}
                    image = f.parent / "image.png"
                else:
                    source = json.loads(f.read_text())
                    prompt = source["prompt"]
                    extra = {"max_tokens": source["max_output_tokens"],
                             "schema": json.loads((root / "source_snapshot/policies/tabletennis/tactical-v1/schema.json").read_text())}
                    image = f.parent / "observation.png"
                raw = image.read_bytes()
                name = f"{game}/{i:03d}.png"
                add(name, raw)
                records.append({"game": game, "prompt": prompt, "system": system,
                    "image_paths": [name], "image_sha256": [hashlib.sha256(raw).hexdigest()],
                    "provenance": {"source_file": str(f), "source_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                                   "collection": "retained native gameplay public observation"},
                    **extra})
        add("records.json", json.dumps(records, indent=2).encode())


if __name__ == "__main__":
    main()
