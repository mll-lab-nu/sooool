"""Combine native/retained sources without introducing evaluator-only inputs."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_export(path):
    rows = json.loads(path.read_text())
    for row in rows:
        row["image_paths"] = [str((path.parent / name).resolve()) for name in row["image_paths"]]
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sports", type=Path, required=True)
    p.add_argument("--asterix", type=Path, required=True)
    p.add_argument("--racing", type=Path, required=True)
    p.add_argument("--touhou", type=Path, required=True)
    p.add_argument("--roadster", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    rows = load_export(a.sports) + load_export(a.asterix) + load_export(a.racing)
    fixture = json.loads((a.touhou / "fixtures.json").read_text())
    schema = json.loads((a.touhou / "schema.json").read_text())
    for case in fixture["fixtures"]:
        rows.append({"game": "touhou", "prompt": case["prompt"],
            "image_paths": [str(a.touhou / name) for name in case["images"]],
            "schema": schema, "max_tokens": 512,
            "provenance": {"source": str(a.touhou / "fixtures.json"), "name": case["name"],
                           "collection": fixture["kind"]}})
    source = ROOT / "artifacts/rhythm/selected"
    rhythm = [json.loads(line) for line in (source / "requests.jsonl").read_text().splitlines()]
    rhythm.sort(key=lambda r: r["version"])
    for i in range(min(30, len(rhythm))):
        case = rhythm[round(i*(len(rhythm)-1)/max(1,min(30,len(rhythm))-1))]
        rows.append({"game": "rhythm", "prompt": case["prompt"],
            "image_paths": [str(source / image) for image in case["frames"]],
            "commentary": True, "max_tokens": 512,
            "provenance": {"source": str(source / "requests.jsonl"), "version": case["version"],
                           "collection": "retained selected-v21 native observations"}})
    road = json.loads((a.roadster / "protocol.json").read_text())
    road_schema = {
        "type": "object", "additionalProperties": False,
        "required": ["keys", "duration_ms", "summary"],
        "properties": {
            "keys": {"type": "array", "maxItems": 4, "uniqueItems": True,
                     "items": {"enum": ["ArrowLeft","ArrowRight","Space","KeyW","KeyS","KeyQ","KeyE"]}},
            "duration_ms": {"type": "integer", "minimum": 50, "maximum": 1000},
            "summary": {"type": "string", "maxLength": 120}}}
    for case in road["inputs"]:
        rows.append({"game": "roadster", "prompt": road["prompt"], "schema": road_schema,
            "image_paths": [str(a.roadster / case["file"])], "image_sha256": [case["sha256"]],
            "max_tokens": road["max_tokens"],
            "provenance": {"source": str(a.roadster / "protocol.json"), "image": case["file"],
                           "collection": "retained seeded native scripted trajectory"}})
    with a.output.open("x") as f:
        json.dump(rows, f, indent=2)
    print(json.dumps({g: sum(r["game"] == g for r in rows) for g in sorted({r["game"] for r in rows})}))


if __name__ == "__main__":
    main()
