#!/usr/bin/env python3
"""Verify locked upstream artifacts; never update a pin automatically."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def verify_stream(stream, expected):
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("SHA-256 mismatch: upstream bytes changed; refusing to use them")


def load_lock(path):
    lock = json.loads(path.read_text())
    if lock.get("schema") != 1:
        raise ValueError("Unsupported dependency lock schema")
    mcp = lock["ssh_mcp"]
    if not re.fullmatch(r"[0-9a-f]{40}", mcp["commit"]):
        raise ValueError("SSH-MCP must be pinned to a full commit SHA")
    if mcp["url"] != "https://codeload.github.com/slepp/ssh-mcp/tar.gz/" + mcp["commit"]:
        raise ValueError("SSH-MCP URL must use the locked commit, not a floating branch")
    for arch, artifact in lock["tunnel_client"]["artifacts"].items():
        expected_url = ("https://github.com/openai/tunnel-client/releases/download/v"
                        + lock["tunnel_client"]["version"] + "/tunnel-client-v"
                        + lock["tunnel_client"]["version"] + "-linux-" + arch + ".zip")
        if artifact["url"] != expected_url:
            raise ValueError("Tunnel client URL must use the locked release")
    artifacts = [("ssh_mcp", mcp), *[("tunnel_client/" + a, x)
                  for a, x in lock["tunnel_client"]["artifacts"].items()]]
    for name, artifact in artifacts:
        if not artifact["url"].startswith("https://") or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise ValueError("Invalid URL or SHA-256 for " + name)
    return lock, artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Check lock/installer consistency without downloading")
    args = parser.parse_args()
    lock, artifacts = load_lock(ROOT / "dependencies.lock.json")
    script = (ROOT / "scripts/bootstrap-debian.sh").read_text()
    # The standalone bootstrap keeps its own pins so it can also run on its own.
    # Refuse a release in which the public lock and actual installer disagree.
    for value in (lock["ssh_mcp"]["commit"], lock["ssh_mcp"]["sha256"],
                  *[a["sha256"] for a in lock["tunnel_client"]["artifacts"].values()]):
        if value not in script:
            raise ValueError("Dependency lock and bootstrap disagree")
    for name, artifact in artifacts:
        if args.offline:
            continue
        with urllib.request.urlopen(artifact["url"], timeout=60) as response:
            verify_stream(response, artifact["sha256"])
        print("Verified " + name)
    print("Dependency pins verified" + (" (offline consistency only)" if args.offline else ""))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Dependency verification failed: " + str(error), file=sys.stderr)
        sys.exit(1)
