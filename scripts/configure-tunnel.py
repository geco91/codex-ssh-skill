#!/usr/bin/env python3
"""Guide local tunnel setup using the pinned client's native runtime manager."""
import argparse
import getpass
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import warnings

TUNNELS_URL = "https://platform.openai.com/settings/organization/tunnels"
KEYS_URL = "https://platform.openai.com/settings/organization/api-keys"
HOME_DIR = Path("/var/lib/codex-test")
CONFIG_DIR = HOME_DIR / ".config/codex-ssh/guided"
CLIENT = "/opt/codex-ssh/tunnel-client"
MCP = str(HOME_DIR / "mcp/bin/ssh-mcp")
ALIAS = "codex-ssh-guided"


def validate_tunnel_id(value):
    if not re.fullmatch(r"tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}", value):
        raise ValueError("Paste the complete tunnel ID from Platform tunnel settings")
    return value


def private_file(path, value, uid, gid):
    # Exclusive creation also rejects symlinks and preserves existing credentials.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(value)
        f.flush()
        os.fsync(f.fileno())
        os.fchown(f.fileno(), uid, gid)


def check_key_reference(path):
    # Inspect metadata only; never rotate/read a saved key to recover setup.
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0 or path.stat().st_mode & 0o777 != 0o600:
        raise RuntimeError("Existing key must be a nonempty regular file with mode 0600; inspect locally, do not overwrite")


def connect_args(tunnel_id, key_file):
    return ["runtimes", "connect", "--alias", ALIAS, "--tunnel-id", tunnel_id,
            "--profile", ALIAS, "--profile-dir", str(CONFIG_DIR / "profiles"),
            "--mcp-command", MCP, "--runtime-api-key", "file:" + str(key_file), "--json"]


def is_ready(status):
    return all(status.get(k) is True for k in ("process_running", "healthy", "ready"))


def client_call(arguments, log_dir=CONFIG_DIR):
    # runuser establishes the service account's HOME and SSH config on this host.
    result = subprocess.run(["runuser", "-u", "codex-test", "--", CLIENT, *arguments],
                            cwd=HOME_DIR, capture_output=True, text=True, timeout=60)
    # Do not echo arbitrary client output, metadata, IDs or secret-bearing diagnostics.
    log = log_dir / "last-client-output.log"
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(result.stdout + "\n" + result.stderr)
    if result.returncode:
        raise RuntimeError(f"tunnel-client exited {result.returncode}; inspect the private local log at {log}")
    return json.loads(result.stdout) if "--json" in arguments else {}


def check_available(aliases, tunnel_id=None):
    for alias in aliases.get("aliases", []):
        if alias.get("alias") == ALIAS:
            if tunnel_id is None or alias.get("tunnel_id") != tunnel_id:
                raise RuntimeError("Runtime alias already exists outside this setup; preserve it and inspect runtimes list")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="Check this setup's existing runtime without prompting")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run on the local Debian/Proxmox host as root")
    account = pwd.getpwnam("codex-test")
    for parent in [HOME_DIR / ".config", HOME_DIR / ".config/codex-ssh", CONFIG_DIR]:
        if parent.is_symlink():
            raise RuntimeError("Refusing a symlinked configuration directory")
        parent.mkdir(mode=0o700, exist_ok=True)
        os.chown(parent, account.pw_uid, account.pw_gid)
        os.chmod(parent, 0o700)
    state_file = CONFIG_DIR / "setup-state.json"
    key_file = CONFIG_DIR / "runtime-key"
    if state_file.is_symlink() or key_file.is_symlink():
        raise RuntimeError("Refusing symlinked setup state or credentials")
    if args.status:
        if not state_file.exists():
            raise RuntimeError("No guided setup state exists yet")
        status = client_call(["runtimes", "status", ALIAS, "--json"])
    else:
        print("\nTunnel setup — this attaches an existing tunnel; it does not create one.")
        print("1. Create/reuse your tunnel: " + TUNNELS_URL)
        print("   Associate the intended Platform organization and ChatGPT workspace.")
        print("2. Create a restricted runtime key: " + KEYS_URL)
        print("   Grant Tunnels Read + Use. Do not use an admin key here.")
        print("   Feature availability also depends on account/workspace permissions.")
        if state_file.exists():
            state = json.loads(state_file.read_text())
            tunnel_id = validate_tunnel_id(state["tunnel_id"])
            check_available(client_call(["runtimes", "list", "--json"]), tunnel_id)
            check_key_reference(key_file)
            with open("/dev/tty", "r", encoding="utf-8") as reader, open("/dev/tty", "w", encoding="utf-8") as writer:
                writer.write("Existing guided setup found. Restart/reuse this same runtime? [y/N] "); writer.flush()
                if reader.readline().strip().lower() not in ("y", "yes"):
                    print("Phase 2/3: existing setup preserved; readiness not checked. Use --status to inspect it.")
                    print("Phase 3/3: product connection NOT TESTED.")
                    return
        else:
            check_available(client_call(["runtimes", "list", "--json"]))
            with open("/dev/tty", "r", encoding="utf-8") as reader, open("/dev/tty", "w", encoding="utf-8") as writer:
                writer.write("Tunnel ID (Enter to finish setup later): "); writer.flush()
                entered = reader.readline()
                if not entered or not entered.strip():
                    print("Phase 2/3: tunnel configuration skipped. Resume: python3 /opt/codex-ssh/configure-tunnel.py")
                    print("Phase 3/3: product connection NOT TESTED.")
                    return
                tunnel_id = validate_tunnel_id(entered.strip())
                if not key_file.exists():
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", getpass.GetPassWarning)
                        key = getpass.getpass("Runtime API key (hidden): ", stream=writer).strip()
                    if not key or any(c.isspace() for c in key):
                        raise ValueError("The runtime key must be nonempty and contain no whitespace")
                    private_file(key_file, key + "\n", account.pw_uid, account.pw_gid)
                    del key
                else:
                    print("Reusing the protected key from interrupted setup; keep the same tunnel ID.")
                check_key_reference(key_file)
                private_file(state_file, json.dumps({"tunnel_id": tunnel_id, "alias": ALIAS}) + "\n",
                             account.pw_uid, account.pw_gid)
        print("Starting the native managed runtime as codex-test...")
        client_call(connect_args(tunnel_id, key_file))
        client_call(["doctor", "--profile", ALIAS, "--profile-dir", str(CONFIG_DIR / "profiles"), "--explain"])
        status = client_call(["runtimes", "status", ALIAS, "--json"])
    flags = {k: status.get(k) for k in ("process_running", "healthy", "ready")}
    print("Runtime status: " + json.dumps(flags))
    if not is_ready(status):
        raise RuntimeError("Runtime not yet confirmed ready; check the private log and native runtime status")
    print("SUCCESS: phase 2/3 complete — tunnel process running, healthy and ready.")
    print("Phase 3/3: product connection NOT TESTED; no end-to-end PASS claimed.")
    print("Next: open https://chatgpt.com/plugins, add a custom MCP server, choose Tunnel,")
    print("select your tunnel, then import the Codex SSH skill ZIP in the supported skill UI.")
    print("For Codex CLI/IDE copy the skill folder to your project's .agents/skills/.")
    print("Local readiness does not prove reboot persistence. This installer does not configure tunnel autostart.")
    print("After reboot: python3 /opt/codex-ssh/configure-tunnel.py — choose reuse to reconnect with saved keys.")
    print("First task: use $codex-ssh to verify the assigned host identity before making changes.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print("Setup stopped: " + (str(error) or "interrupted") + ". Existing state is preserved.", file=sys.stderr)
        sys.exit(1)
