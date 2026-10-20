"""Create exactly one four-hour H200 experiment after offline corpus validation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.local_profile import read_corpus
from scripts.build_local_profile_corpus import GAMES


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--ssh-public-key", type=Path, required=True)
    p.add_argument("--image", required=True, help="Verified immutable accelerator OS image name")
    p.add_argument("--name", default="sooool-deepseek-1017-h200")
    p.add_argument("--project", default="thematic-axle-508622-j7")
    p.add_argument("--zone", default="us-central1-b")
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    rows = read_corpus(a.corpus)
    if {r["game"] for r in rows} != GAMES:
        raise ValueError("All seven tasks must be prepared before renting GPUs")
    pub = a.ssh_public_key.read_text().strip()
    if not pub.startswith(("ssh-ed25519 ", "ssh-rsa ")):
        raise ValueError("Expected a public SSH key, never a private key")
    key_file = a.corpus.parent / "instance-ssh-public-key.txt"
    key_file.write_text("ubuntu:" + pub + "\n")
    command = [
        "gcloud", "compute", "instances", "create", a.name,
        "--project="+a.project, "--zone="+a.zone,
        "--machine-type=a3-ultragpu-8g",
        "--provisioning-model=FLEX_START", "--request-valid-for-duration=600s",
        "--max-run-duration=14400s", "--instance-termination-action=DELETE",
        "--maintenance-policy=TERMINATE", "--no-restart-on-failure",
        "--image="+a.image, "--image-project=ubuntu-os-accelerator-images",
        "--boot-disk-type=hyperdisk-balanced", "--boot-disk-size=1000GB",
        "--boot-disk-auto-delete", "--network-interface=network=default,nic-type=GVNIC",
        "--no-service-account", "--no-scopes",
        "--labels=purpose=sooool-latency,model=deepseek-1017",
        "--metadata=block-project-ssh-keys=TRUE",
        "--metadata-from-file=startup-script="+str(ROOT / "scripts/local_profile_h200_boot.sh")
        +",ssh-keys="+str(key_file),
        "--format=json", "--quiet",
    ]
    print(json.dumps({"command": command, "max_run_seconds": 14400,
                      "gpu_cost_estimate_usd": 169.60, "extra_disk_network_costs": True}, indent=2))
    if a.execute:
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
